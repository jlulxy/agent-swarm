"""
Master Agent - 主控制器

核心职责：
1. 任务分析与角色涌现
2. Subagent 创建与并行调度
3. 中继站协调（集中式）
4. 结果整合与报告生成
"""

import asyncio
import uuid
import json
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from datetime import datetime

from core.models import (
    TaskSession,
    TaskPlan,
    SubagentState,
    AgentStatus,
    RelayMessage,
    RelayType,
    HumanIntervention,
    InterventionType,
    InterventionScope,
)
from core.role_emergence import RoleEmergenceEngine
from core.subagent import SubagentRuntime
from core.relay_station import RelayStationCoordinator, AdaptiveRelayTrigger
from llm.provider import LLMProviderFactory, LLMMessage, LLMConfig
from agui.events import (
    EventFactory,
    BaseEvent,
    RunStartedEvent,
    RunFinishedEvent,
    AgentSpawnedEvent,
    AgentStatusChangedEvent,
    AgentProgressEvent,
    AgentThinkingEvent,
    RelayStationOpenedEvent,
    RelayMessageSentEvent,
    RelayStationClosedEvent,
    PlanGeneratedEvent,
    RoleEmergedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallResultEvent,
)


class MasterAgent:
    """主 Agent - 整个集群的控制中心
    
    重要：每个 MasterAgent 实例对应一个独立的会话（session）
    不同会话之间的数据完全隔离，包括：
    - 任务会话 (sessions)
    - 活跃 Subagent (active_subagents)
    - 中继站协调器 (relay_coordinator)
    - 消息历史和干预历史
    """
    
    def __init__(
        self,
        provider_type: str = "openai",
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Args:
            provider_type: LLM 提供者类型 (openai/claude)
            model: 模型名称
            session_id: 会话 ID（用于数据隔离标识）
            user_id: 用户 ID（用于记忆系统关联）
        """
        self.provider_type = provider_type
        self.model = model
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        
        # 核心引擎
        self.role_engine = RoleEmergenceEngine(provider_type, model)
        
        # 创建中继协调器，设置回调用于 SSE 事件通知
        # 注意：每个 MasterAgent 实例有自己独立的 RelayStationCoordinator
        self.relay_coordinator = RelayStationCoordinator(
            on_message_broadcast=self._on_relay_message_broadcast,
            on_intervention_broadcast=self._on_intervention_broadcast,
            session_id=self.session_id,  # 传入 session_id 用于日志和调试
        )
        self.relay_trigger = AdaptiveRelayTrigger()
        
        # 待发送的 SSE 事件队列（用于在干预时推送事件）
        self.pending_relay_events: List[RelayMessageSentEvent] = []
        
        # LLM 用于结果整合
        self.provider = LLMProviderFactory.get_provider(provider_type)
        self.llm_config = LLMProviderFactory.get_default_config(provider_type)
        if model:
            self.llm_config.model = model
        
        # 会话管理 - 本实例专属
        # 注意：这里的 sessions 是本 MasterAgent 内部的任务会话，
        # 与外层 SessionManager 管理的"用户会话"不同
        self.sessions: Dict[str, TaskSession] = {}
        self.active_subagents: Dict[str, SubagentRuntime] = {}
        
        # 当前活跃的任务会话 ID
        self.current_task_session_id: Optional[str] = None
        
        # 事件队列（用于 SSE 输出）
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        print(f"[MasterAgent] Created new instance for session: {self.session_id[:8]}...")
    
    async def execute_task(
        self, 
        task: str,
        previous_context: Optional[str] = None,
        previous_roles: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[BaseEvent, None]:
        """
        执行任务 - 完整流程
        
        1. 任务分析与角色涌现
        2. 创建 Subagents
        3. 并行执行 + 中继协调
        4. 结果整合
        
        Args:
            task: 任务描述
            previous_context: 追问场景下的上一轮摘要上下文（可选）
            previous_roles: 追问场景下的上一轮角色配置（可选，用于角色复用）
        
        Yields:
            AG-UI 协议事件流
        """
        # 创建会话
        session = TaskSession(task=task)
        self.sessions[session.id] = session
        
        thread_id = session.id
        run_id = str(uuid.uuid4())
        
        # 发送开始事件
        yield EventFactory.run_started(thread_id, run_id)
        
        try:
            # ===== 用户记忆检索 =====
            user_memory_text = ""
            if self.user_id:
                try:
                    from memory.service import get_memory_service
                    memory_service = get_memory_service()
                    if memory_service.is_enabled:
                        memories = await memory_service.retrieve(
                            user_id=self.user_id,
                            queries=[task],
                        )
                        user_memory_text = memory_service.format_for_prompt(memories)
                        if user_memory_text:
                            print(f"[MasterAgent] Retrieved user memory for {self.user_id[:8]}...")
                        
                        # 实时摄入用户输入
                        asyncio.create_task(memory_service.memorize(
                            user_id=self.user_id,
                            content=f"用户任务请求: {task}",
                            modality="conversation",
                        ))
                except Exception as e:
                    print(f"[MasterAgent] Memory retrieval failed (non-blocking): {e}")
            
            # ===== 合并上下文：用户记忆 + 追问上下文 =====
            combined_context = ""
            if user_memory_text:
                combined_context += user_memory_text
            if previous_context:
                if combined_context:
                    combined_context += "\n\n"
                combined_context += f"## 上一轮任务上下文\n{previous_context}"
                print(f"[MasterAgent] Followup mode: injecting previous context ({len(previous_context)} chars)")
            
            # ===== 阶段1: 任务分析与角色涌现 =====
            session.status = AgentStatus.PLANNING
            
            yield TextMessageStartEvent(message_id=f"planning-{run_id}", role="assistant")
            
            if previous_context:
                yield TextMessageContentEvent(
                    message_id=f"planning-{run_id}",
                    delta="🔄 基于上一轮结果继续分析，规划角色涌现...\n\n"
                )
            else:
                yield TextMessageContentEvent(
                    message_id=f"planning-{run_id}",
                    delta="🔍 正在分析任务，规划角色涌现...\n\n"
                )
            
            # 调用角色涌现引擎（传入 previous_roles 支持角色复用）
            async for event in self._emerge_roles(
                session, run_id, 
                user_memory=combined_context or "",
                previous_roles=previous_roles
            ):
                yield event
            
            if not session.plan:
                yield TextMessageContentEvent(
                    message_id=f"planning-{run_id}",
                    delta="❌ 角色涌现失败\n"
                )
                yield TextMessageEndEvent(message_id=f"planning-{run_id}")
                return
            
            yield TextMessageEndEvent(message_id=f"planning-{run_id}")
            
            # 发送规划完成事件
            yield PlanGeneratedEvent(
                plan_id=session.plan.id,
                original_task=session.plan.original_task,
                analysis=session.plan.analysis,
                phases=session.plan.phases,
                estimated_duration=session.plan.estimated_duration,
                total_agents=len(session.plan.subagent_configs)
            )
            
            # ===== 阶段2: 创建 Subagents =====
            yield TextMessageStartEvent(message_id=f"spawning-{run_id}", role="assistant")
            yield TextMessageContentEvent(
                message_id=f"spawning-{run_id}",
                delta=f"\n🤖 正在生成 {len(session.plan.subagent_configs)} 个 Subagent...\n\n"
            )
            
            subagents = await self._spawn_subagents(session, combined_context or "")
            
            for subagent in subagents:
                role = subagent.config.role
                
                # 构建方法论字典
                methodology_dict = None
                if role.methodology:
                    methodology_dict = {
                        "approach": role.methodology.approach,
                        "steps": role.methodology.steps,
                        "tools_and_frameworks": role.methodology.tools_and_frameworks,
                        "success_criteria": role.methodology.success_criteria,
                        "quality_metrics": role.methodology.quality_metrics
                    }
                
                # 构建技能列表
                skills_list = [
                    {
                        "skill_name": s.skill_name,
                        "skill_display_name": s.skill_display_name,
                        "reason": s.reason
                    }
                    for s in role.assigned_skills
                ]
                
                yield AgentSpawnedEvent(
                    agent_id=subagent.agent_id,
                    agent_name=subagent.agent_name,
                    role_name=role.name,
                    role_description=role.description,
                    capabilities=role.capabilities,
                    task_segment=subagent.config.task_segment,
                    work_objective=role.work_objective,
                    deliverables=role.deliverables,
                    methodology=methodology_dict,
                    assigned_skills=skills_list,
                    expertise_level=role.expertise_level,
                    focus_areas=role.focus_areas
                )
                yield TextMessageContentEvent(
                    message_id=f"spawning-{run_id}",
                    delta=f"  ✅ {role.name} - {role.description[:50]}...\n"
                )
            
            yield TextMessageEndEvent(message_id=f"spawning-{run_id}")
            
            # ===== 阶段3: 并行执行 =====
            session.status = AgentStatus.RUNNING
            
            yield TextMessageStartEvent(message_id=f"executing-{run_id}", role="assistant")
            yield TextMessageContentEvent(
                message_id=f"executing-{run_id}",
                delta="\n⚡ 所有 Subagent 开始并行工作...\n\n"
            )
            yield TextMessageEndEvent(message_id=f"executing-{run_id}")
            
            # 打开第一个中继站
            if session.plan.relay_stations:
                first_station = session.plan.relay_stations[0]
                first_station.participating_agents = [s.agent_id for s in subagents]
                await self.relay_coordinator.open_station(first_station.id)
                
                yield RelayStationOpenedEvent(
                    station_id=first_station.id,
                    station_name=first_station.name,
                    phase=first_station.phase,
                    participating_agents=[
                        {"id": s.agent_id, "name": s.agent_name}
                        for s in subagents
                    ]
                )
            
            # 并行执行所有 Subagent
            async for event in self._execute_subagents_parallel(session, subagents):
                yield event
            
            # ===== 阶段4: 结果整合 =====
            yield TextMessageStartEvent(message_id=f"integrating-{run_id}", role="assistant")
            yield TextMessageContentEvent(
                message_id=f"integrating-{run_id}",
                delta="\n\n📝 所有 Subagent 完成工作，正在整合结果...\n\n"
            )
            
            async for event in self._integrate_results(session, run_id):
                yield event
            
            yield TextMessageEndEvent(message_id=f"integrating-{run_id}")
            
            # 完成
            session.status = AgentStatus.COMPLETED
            
            # 异步摄入任务完成后的完整对话结果
            if self.user_id:
                try:
                    from memory.service import get_memory_service
                    memory_service = get_memory_service()
                    if memory_service.is_enabled:
                        # 收集用户在本轮的所有发言（task + 介入消息），不摄入 AI 产出
                        user_utterances = [f"用户任务: {task}"]
                        # 从 intervention_history 提取用户的 inject 消息（这些是用户在对话中说的话）
                        for intervention in self.relay_coordinator.intervention_history:
                            if intervention.type == InterventionType.INJECT:
                                info = intervention.payload.get("information", "")
                                if info:
                                    user_utterances.append(f"用户说: {info}")
                            elif intervention.reason:
                                user_utterances.append(f"用户指令: {intervention.reason}")
                        
                        memorize_content = "\n".join(user_utterances)
                        asyncio.create_task(memory_service.memorize(
                            user_id=self.user_id,
                            content=memorize_content,
                            modality="conversation",
                        ))
                except Exception as e:
                    print(f"[MasterAgent] Memory memorize failed (non-blocking): {e}")
            
            yield EventFactory.run_finished(thread_id, run_id)
            
        except Exception as e:
            session.status = AgentStatus.FAILED
            yield EventFactory.run_error(str(e))
    
    async def _emerge_roles(
        self,
        session: TaskSession,
        run_id: str,
        user_memory: str = "",
        previous_roles: Optional[List[Dict]] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """角色涌现阶段"""
        try:
            context = user_memory if user_memory else None
            async for event in self.role_engine.analyze_and_emerge_stream(
                session.task, context, previous_roles=previous_roles
            ):
                if event["type"] == "chunk":
                    yield TextMessageContentEvent(
                        message_id=f"planning-{run_id}",
                        delta=event["content"]
                    )
                elif event["type"] == "plan":
                    session.plan = event["plan"]
                    
                    # 为每个涌现的角色发送事件
                    for role in session.plan.emergent_roles:
                        yield RoleEmergedEvent(
                            role_id=role.id,
                            role_name=role.name,
                            description=role.description,
                            capabilities=role.capabilities,
                            focus_areas=role.focus_areas,
                            reasoning=f"基于任务分析自动涌现"
                        )
                    
                    yield TextMessageContentEvent(
                        message_id=f"planning-{run_id}",
                        delta=f"\n\n✅ 成功涌现 {len(session.plan.emergent_roles)} 个角色\n"
                    )
                elif event["type"] == "error":
                    yield TextMessageContentEvent(
                        message_id=f"planning-{run_id}",
                        delta=f"\n\n❌ 角色涌现错误: {event['error']}\n"
                    )
        except Exception as e:
            yield TextMessageContentEvent(
                message_id=f"planning-{run_id}",
                delta=f"\n\n❌ 角色涌现异常: {str(e)}\n"
            )
    
    async def _spawn_subagents(self, session: TaskSession, user_memory: str = "") -> List[SubagentRuntime]:
        """创建 Subagents"""
        subagents = []
        
        # 清理旧的 agent 注册，避免之前任务的 agent 残留
        # 保留 agent_callbacks 中的注册，但只处理当前会话的 agent
        old_agent_ids = list(self.relay_coordinator.agent_callbacks.keys())
        for old_id in old_agent_ids:
            if old_id not in session.subagent_states:
                self.relay_coordinator.unregister_agent(old_id)
                print(f"[MasterAgent] Cleaned up old agent registration: {old_id[:8]}...")
        
        for config in session.plan.subagent_configs:
            # 创建 Subagent 运行时
            subagent = SubagentRuntime(
                config=config,
                provider_type=self.provider_type,
                model=self.model,
                on_relay_request=lambda msg: asyncio.create_task(
                    self.relay_coordinator.broadcast_message(msg)
                ),
                user_memory=user_memory,
            )
            
            # 注册到中继协调器 - 同时注册普通回调和干预处理器
            self.relay_coordinator.register_agent(
                subagent.agent_id,
                subagent.receive_relay_message,
                intervention_handler=subagent.receive_intervention  # 添加干预处理器
            )
            
            # 初始化状态
            session.subagent_states[subagent.agent_id] = subagent.state
            self.active_subagents[subagent.agent_id] = subagent
            
            subagents.append(subagent)
        
        return subagents
    
    async def _execute_subagents_parallel(
        self,
        session: TaskSession,
        subagents: List[SubagentRuntime]
    ) -> AsyncGenerator[BaseEvent, None]:
        """并行执行所有 Subagents"""
        
        # 双队列设计：status/error 事件走高优先级队列，其他事件走普通队列
        # 这样 status:completed 不会被大量 thinking/progress 事件阻塞
        priority_queue = asyncio.Queue()  # status, error, result 等关键事件
        normal_queue = asyncio.Queue()    # thinking, progress 等高频事件
        
        # 高优先级事件类型
        PRIORITY_EVENT_TYPES = {"status", "error", "result"}
        
        async def run_subagent_with_events(subagent: SubagentRuntime):
            """运行单个 Subagent 并收集事件"""
            previous_status = subagent.state.status
            
            async for event in subagent.run_stream():
                event["agent_id"] = subagent.agent_id
                event["agent_name"] = subagent.agent_name
                # 根据事件类型分流到不同队列
                if event["type"] in PRIORITY_EVENT_TYPES:
                    await priority_queue.put(event)
                else:
                    await normal_queue.put(event)
            
            # 更新会话状态
            session.subagent_states[subagent.agent_id] = subagent.state
        
        def _convert_event(event) -> Optional[BaseEvent]:
            """将原始事件字典转换为 AG-UI 事件对象，返回 None 则跳过"""
            agent_id = event.get("agent_id", "")
            agent_name = event.get("agent_name", "")
            event_type = event["type"]
            
            if event_type == "status":
                return AgentStatusChangedEvent(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    previous_status="running",
                    new_status=event["status"]
                )
            elif event_type == "progress":
                return AgentProgressEvent(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    progress=event["progress"],
                    current_step=event["step"],
                    iterations=event.get("iterations", 0)
                )
            elif event_type == "thinking":
                return AgentThinkingEvent(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    thinking=event["delta"]
                )
            elif event_type == "relay":
                relay_data = event["message"]
                return RelayMessageSentEvent(
                    station_id=self.relay_coordinator.active_station_id or "",
                    message_id=relay_data.get("id", ""),
                    source_agent_id=relay_data.get("source_agent_id", ""),
                    source_agent_name=relay_data.get("source_agent_name", ""),
                    target_agent_ids=relay_data.get("target_agent_ids", []),
                    relay_type=relay_data.get("type", ""),
                    content=relay_data.get("content", ""),
                    importance=relay_data.get("importance", 0.5),
                    metadata=relay_data.get("metadata", {}),
                    viewed_by=relay_data.get("viewed_by", []),
                    acknowledged_by=relay_data.get("acknowledged_by", []),
                    viewed_timestamps=relay_data.get("viewed_timestamps", {}),
                )
            elif event_type == "tool_call_start":
                return ToolCallStartEvent(
                    tool_call_id=event.get("tool_call_id", ""),
                    tool_call_name=event.get("tool_name", ""),
                    parent_message_id=agent_id,
                )
            elif event_type == "tool_call_result":
                return ToolCallResultEvent(
                    tool_call_id=event.get("tool_call_id", ""),
                    result=json.dumps({
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "skill_name": event.get("skill_name", ""),
                        "success": event.get("success", False),
                        "summary": event.get("summary", ""),
                        "result_preview": event.get("result_preview", ""),
                    }, ensure_ascii=False),
                )
            # result, completion_blocked, relay_processed 等事件不需要转发给前端
            return None
        
        # 启动所有 Subagent
        tasks = [
            asyncio.create_task(run_subagent_with_events(subagent))
            for subagent in subagents
        ]
        
        # 收集并发出事件
        completed_count = 0
        total_count = len(subagents)
        
        while completed_count < total_count:
            # 阶段1：始终先清空优先队列（status/error/result 事件立即送达）
            while not priority_queue.empty():
                try:
                    event = priority_queue.get_nowait()
                    event_type = event["type"]
                    
                    if event_type == "status":
                        new_status = event["status"]
                        if new_status in [AgentStatus.COMPLETED.value, AgentStatus.FAILED.value]:
                            completed_count += 1
                    elif event_type == "error":
                        completed_count += 1
                    
                    agui_event = _convert_event(event)
                    if agui_event:
                        yield agui_event
                except asyncio.QueueEmpty:
                    break
            
            # 阶段2：处理普通队列中的一批事件（批量处理以提高吞吐）
            batch_count = 0
            max_batch = 10  # 每轮最多处理 10 个普通事件，然后回头检查优先队列
            while batch_count < max_batch and not normal_queue.empty():
                try:
                    event = normal_queue.get_nowait()
                    agui_event = _convert_event(event)
                    if agui_event:
                        yield agui_event
                    batch_count += 1
                except asyncio.QueueEmpty:
                    break
            
            # 阶段3：如果两个队列都空，短暂等待新事件
            if priority_queue.empty() and normal_queue.empty():
                # 先检查是否所有 subagent 任务都已完成
                done_tasks = [t for t in tasks if t.done()]
                if len(done_tasks) == len(tasks):
                    # 所有任务完成，再排空队列中的残留事件后退出
                    while not priority_queue.empty():
                        try:
                            event = priority_queue.get_nowait()
                            if event["type"] == "status":
                                new_status = event["status"]
                                if new_status in [AgentStatus.COMPLETED.value, AgentStatus.FAILED.value]:
                                    completed_count += 1
                            agui_event = _convert_event(event)
                            if agui_event:
                                yield agui_event
                        except asyncio.QueueEmpty:
                            break
                    while not normal_queue.empty():
                        try:
                            event = normal_queue.get_nowait()
                            agui_event = _convert_event(event)
                            if agui_event:
                                yield agui_event
                        except asyncio.QueueEmpty:
                            break
                    break
                
                # 还有任务在跑，等待新事件到达
                priority_wait = asyncio.create_task(priority_queue.get())
                normal_wait = asyncio.create_task(normal_queue.get())
                
                done, pending = await asyncio.wait(
                    [priority_wait, normal_wait],
                    timeout=0.1,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 处理完成的等待任务
                for finished_task in done:
                    try:
                        event = finished_task.result()
                        event_type = event["type"]
                        
                        if event_type == "status":
                            new_status = event["status"]
                            if new_status in [AgentStatus.COMPLETED.value, AgentStatus.FAILED.value]:
                                completed_count += 1
                        elif event_type == "error":
                            completed_count += 1
                        
                        agui_event = _convert_event(event)
                        if agui_event:
                            yield agui_event
                    except Exception:
                        pass
                
                # 取消未完成的等待任务
                for pending_task in pending:
                    pending_task.cancel()
                    try:
                        await pending_task
                    except (asyncio.CancelledError, Exception):
                        pass
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 关闭中继站
        if self.relay_coordinator.active_station_id:
            summary = await self.relay_coordinator.close_station(
                self.relay_coordinator.active_station_id
            )
            if summary:
                active_station = list(self.relay_coordinator.stations.values())[-1]
                yield RelayStationClosedEvent(
                    station_id=active_station.id,
                    station_name=active_station.name,
                    summary=summary
                )
    
    async def _integrate_results(
        self,
        session: TaskSession,
        run_id: str
    ) -> AsyncGenerator[BaseEvent, None]:
        """整合所有 Subagent 的结果"""
        
        # 收集所有结果
        results = []
        for agent_id, state in session.subagent_states.items():
            if state.final_result:
                results.append({
                    "role": state.config.role.name,
                    "result": state.final_result
                })
        
        # 构建整合提示
        integration_prompt = self._build_integration_prompt(session, results)
        
        messages = [
            LLMMessage(role="system", content=INTEGRATION_SYSTEM_PROMPT.replace(
                "{current_time}", datetime.now().strftime("%Y年%m月%d日 %H:%M:%S（%A）")
            )),
            LLMMessage(role="user", content=integration_prompt)
        ]
        
        # 流式生成最终报告
        final_report = ""
        async for chunk in self.provider.chat(messages, self.llm_config):
            final_report += chunk
            yield TextMessageContentEvent(
                message_id=f"integrating-{run_id}",
                delta=chunk
            )
        
        session.final_report = final_report
    
    def _build_integration_prompt(
        self,
        session: TaskSession,
        results: List[Dict[str, str]]
    ) -> str:
        """构建整合提示"""
        prompt_parts = [
            f"## 原始任务\n{session.task}\n",
            f"## 任务分析\n{session.plan.analysis if session.plan else ''}\n",
        ]
        
        # ===== 重要：首先展示人工干预历史 =====
        # 从中继协调器获取所有人工干预记录
        intervention_history = self.relay_coordinator.intervention_history
        if intervention_history:
            prompt_parts.append("\n## ⚠️ 人工干预记录（重要）\n")
            prompt_parts.append("以下是用户在任务执行过程中发出的所有干预指令，请在整合报告时充分考虑这些指令：\n")
            
            for idx, intervention in enumerate(intervention_history, 1):
                prompt_parts.append(f"### 干预 #{idx}")
                prompt_parts.append(f"- **类型**: {intervention.type.value}")
                prompt_parts.append(f"- **优先级**: {intervention.priority}/10")
                prompt_parts.append(f"- **作用范围**: {intervention.scope.value}")
                
                if intervention.reason:
                    prompt_parts.append(f"- **原因**: {intervention.reason}")
                
                # 根据类型展示具体内容
                if intervention.type == InterventionType.INJECT:
                    info = intervention.payload.get("information", "")
                    if info:
                        prompt_parts.append(f"- **注入内容**:\n  > {info}")
                elif intervention.type == InterventionType.ADJUST:
                    adjustments = intervention.payload.get("adjustments", {})
                    if adjustments:
                        prompt_parts.append("- **调整指令**:")
                        for key, value in adjustments.items():
                            prompt_parts.append(f"  - {key}: {value}")
                
                # 目标 Agent
                if intervention.target_agent_id:
                    prompt_parts.append(f"- **目标Agent**: {intervention.target_agent_id}")
                elif intervention.target_agent_ids:
                    prompt_parts.append(f"- **目标Agents**: {', '.join(intervention.target_agent_ids)}")
                
                prompt_parts.append("")
            
            prompt_parts.append("**请务必在整合报告中体现对上述人工干预指令的响应和考虑。**\n")
        
        # ===== 各角色分析结果 =====
        prompt_parts.append("\n## 各角色分析结果\n")
        for result in results:
            prompt_parts.append(f"### {result['role']}\n{result['result']}\n\n")
        
        # ===== 中继站信息交换记录 =====
        if self.relay_coordinator.message_history:
            # 分离人工干预消息和普通中继消息
            intervention_msgs = []
            regular_msgs = []
            
            for msg in self.relay_coordinator.message_history:
                if msg.type == RelayType.HUMAN_INTERVENTION:
                    intervention_msgs.append(msg)
                else:
                    regular_msgs.append(msg)
            
            # 显示普通中继消息（Agent间的信息交换）
            if regular_msgs:
                prompt_parts.append("\n## Agent间中继信息交换\n")
                for msg in regular_msgs[-15:]:  # 增加到最近15条普通消息
                    # 完整展示消息内容，不再截断
                    prompt_parts.append(
                        f"- [{msg.type.value}] {msg.source_agent_name}: {msg.content}\n"
                    )
        
        prompt_parts.append(
            "\n## 整合要求\n"
            "请基于以上所有信息，整合生成一份完整、专业、深入的分析报告。\n"
            "**特别注意**：\n"
            "1. 如果有人工干预记录，必须在报告中明确体现对干预指令的响应\n"
            "2. 整合各角色的分析结果，消除矛盾，突出共识\n"
            "3. 形成有价值的综合洞察和建议\n"
        )
        
        return "\n".join(prompt_parts)
    
    # ========== 人工干预接口 (升级版 - 通过中继站广播) ==========
    
    async def pause_agent(
        self, 
        agent_id: str, 
        reason: str = "",
        broadcast: bool = True
    ) -> bool:
        """暂停指定 Agent
        
        Args:
            agent_id: 目标 Agent ID
            reason: 暂停原因
            broadcast: 是否广播到中继站
        """
        if agent_id not in self.active_subagents:
            return False
        
        self.active_subagents[agent_id].pause()
        
        if broadcast:
            intervention = HumanIntervention(
                type=InterventionType.PAUSE,
                target_agent_id=agent_id,
                scope=InterventionScope.SINGLE,
                reason=reason or "用户暂停了该 Agent",
                priority=7,
            )
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return True
    
    async def resume_agent(
        self, 
        agent_id: str, 
        reason: str = "",
        broadcast: bool = True
    ) -> bool:
        """恢复指定 Agent
        
        Args:
            agent_id: 目标 Agent ID
            reason: 恢复原因
            broadcast: 是否广播到中继站
        """
        if agent_id not in self.active_subagents:
            return False
        
        self.active_subagents[agent_id].resume()
        
        if broadcast:
            intervention = HumanIntervention(
                type=InterventionType.RESUME,
                target_agent_id=agent_id,
                scope=InterventionScope.SINGLE,
                reason=reason or "用户恢复了该 Agent",
                priority=6,
            )
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return True
    
    async def cancel_agent(
        self, 
        agent_id: str, 
        reason: str = "",
        broadcast: bool = True
    ) -> bool:
        """取消指定 Agent
        
        Args:
            agent_id: 目标 Agent ID
            reason: 取消原因
            broadcast: 是否广播到中继站
        """
        if agent_id not in self.active_subagents:
            return False
        
        self.active_subagents[agent_id].cancel()
        
        if broadcast:
            intervention = HumanIntervention(
                type=InterventionType.CANCEL,
                target_agent_id=agent_id,
                scope=InterventionScope.SINGLE,
                reason=reason or "用户取消了该 Agent 的任务",
                priority=8,
            )
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return True
    
    async def inject_to_agent(
        self, 
        agent_id: str, 
        information: str,
        broadcast: bool = True,
        priority: int = 5
    ) -> bool:
        """向指定 Agent 注入信息
        
        升级版：信息会通过中继站广播，其他 Agent 也能看到
        
        Args:
            agent_id: 目标 Agent ID
            information: 要注入的信息
            broadcast: 是否广播到中继站
            priority: 优先级 (1-10)
        """
        if agent_id not in self.active_subagents:
            return False
        
        # 直接注入到目标 Agent
        self.active_subagents[agent_id].inject_information(information)
        
        # 通过中继站广播（让其他 Agent 知道发生了什么）
        if broadcast:
            intervention = HumanIntervention(
                type=InterventionType.INJECT,
                target_agent_id=agent_id,
                scope=InterventionScope.BROADCAST,  # 广播但不强制执行
                payload={"information": information},
                reason=f"用户向 {self.active_subagents[agent_id].agent_name} 注入了信息",
                priority=priority,
            )
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return True
    
    async def broadcast_to_all_agents(
        self,
        message: str,
        reason: str = "",
        priority: int = 7,
        force_action: bool = False
    ) -> bool:
        """向所有 Agent 广播消息
        
        这是升级后的核心功能：人工指令通过中继站广播给所有 Agent
        
        Args:
            message: 广播消息内容
            reason: 广播原因
            priority: 优先级 (1-10)
            force_action: 是否强制所有 Agent 执行（True=ALL, False=BROADCAST）
        """
        if not self.active_subagents:
            return False
        
        intervention = HumanIntervention(
            type=InterventionType.INJECT,
            target_agent_ids=list(self.active_subagents.keys()),
            scope=InterventionScope.ALL if force_action else InterventionScope.BROADCAST,
            payload={"information": message},
            reason=reason or "用户广播了一条消息",
            priority=priority,
        )
        
        await self.relay_coordinator.broadcast_intervention(intervention)
        
        # 如果强制执行，直接注入到每个 Agent
        if force_action:
            for agent_id, subagent in self.active_subagents.items():
                subagent.inject_information(message)
        
        return True
    
    async def adjust_agent(
        self,
        agent_id: str,
        adjustments: Dict[str, Any],
        reason: str = "",
        broadcast: bool = True
    ) -> bool:
        """调整 Agent 参数或行为
        
        Args:
            agent_id: 目标 Agent ID
            adjustments: 调整参数 (例如: {"focus": "镜头分析", "depth": "更深入"})
            reason: 调整原因
            broadcast: 是否广播
        """
        if agent_id not in self.active_subagents:
            return False
        
        # 将调整转换为注入信息
        adjustment_msg = "请根据以下指示调整你的工作方向：\n"
        for key, value in adjustments.items():
            adjustment_msg += f"- {key}: {value}\n"
        
        self.active_subagents[agent_id].inject_information(adjustment_msg)
        
        if broadcast:
            intervention = HumanIntervention(
                type=InterventionType.ADJUST,
                target_agent_id=agent_id,
                scope=InterventionScope.BROADCAST,
                payload={"adjustments": adjustments},
                reason=reason or f"用户调整了 {self.active_subagents[agent_id].agent_name} 的工作方向",
                priority=6,
            )
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return True
    
    async def apply_intervention(
        self,
        intervention: HumanIntervention
    ) -> bool:
        """应用人工干预（通用接口）
        
        这是最灵活的干预接口，支持所有类型的干预
        """
        # 根据作用范围确定目标
        if intervention.scope == InterventionScope.SINGLE:
            targets = [intervention.target_agent_id] if intervention.target_agent_id else []
        elif intervention.scope == InterventionScope.SELECTED:
            targets = intervention.target_agent_ids
        else:
            targets = list(self.active_subagents.keys())
        
        # 执行干预动作
        success = True
        for target_id in targets:
            if target_id not in self.active_subagents:
                continue
            
            subagent = self.active_subagents[target_id]
            
            if intervention.type == InterventionType.PAUSE:
                subagent.pause()
            elif intervention.type == InterventionType.RESUME:
                subagent.resume()
            elif intervention.type == InterventionType.CANCEL:
                subagent.cancel()
            elif intervention.type == InterventionType.INJECT:
                info = intervention.payload.get("information", "")
                if info:
                    subagent.inject_information(info)
            elif intervention.type == InterventionType.ADJUST:
                adjustments = intervention.payload.get("adjustments", {})
                if adjustments:
                    adjustment_msg = "请根据以下指示调整你的工作方向：\n"
                    for key, value in adjustments.items():
                        adjustment_msg += f"- {key}: {value}\n"
                    subagent.inject_information(adjustment_msg)
        
        # 广播干预消息
        if intervention.broadcast_to_relay:
            await self.relay_coordinator.broadcast_intervention(intervention)
        
        return success
    
    # ========== 中继消息回调（用于 SSE 事件推送） ==========
    
    def _on_relay_message_broadcast(self, station_id: str, message: RelayMessage):
        """
        中继消息广播回调 - 将消息转换为 SSE 事件存储
        
        这个回调在中继消息广播时被调用，用于生成前端可用的事件
        """
        # 确保 station_id 有值
        effective_station_id = station_id or "default-intervention-station"
        
        event = RelayMessageSentEvent(
            station_id=effective_station_id,
            message_id=message.id,
            source_agent_id=message.source_agent_id,
            source_agent_name=message.source_agent_name,
            target_agent_ids=message.target_agent_ids,
            relay_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            content=message.content,
            importance=message.importance,
            metadata=message.metadata,
            viewed_by=message.viewed_by,
            acknowledged_by=message.acknowledged_by,
            viewed_timestamps=message.viewed_timestamps,
        )
        # 存储事件，稍后可以通过轮询获取
        self.pending_relay_events.append(event)
        print(f"[MasterAgent] Relay message broadcast: {message.id}, type={message.type.value}, station={effective_station_id}")
    
    def _on_intervention_broadcast(
        self, 
        station_id: str, 
        message: RelayMessage, 
        intervention: HumanIntervention
    ):
        """
        人工干预广播回调 - 将干预消息转换为 SSE 事件
        
        这个回调在人工干预通过中继站广播时被调用
        """
        # 确保 station_id 有值，如果为空则使用默认值
        effective_station_id = station_id or "default-intervention-station"
        
        event = RelayMessageSentEvent(
            station_id=effective_station_id,
            message_id=message.id,
            source_agent_id=message.source_agent_id,
            source_agent_name=message.source_agent_name,
            target_agent_ids=message.target_agent_ids,
            relay_type=message.type.value if hasattr(message.type, 'value') else str(message.type),
            content=message.content,
            importance=message.importance,
            metadata=message.metadata,
            viewed_by=message.viewed_by,
            acknowledged_by=message.acknowledged_by,
            viewed_timestamps=message.viewed_timestamps,
        )
        self.pending_relay_events.append(event)
        print(f"[MasterAgent] Intervention broadcast: {intervention.id}, type={intervention.type.value}, station={effective_station_id}, targets={message.target_agent_ids}")
    
    def get_pending_relay_events(self) -> List[RelayMessageSentEvent]:
        """获取并清空待发送的中继事件"""
        events = self.pending_relay_events.copy()
        self.pending_relay_events.clear()
        return events
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "id": session.id,
            "task": session.task,
            "status": session.status.value,
            "plan": session.plan.model_dump() if session.plan else None,
            "subagents": {
                aid: state.model_dump()
                for aid, state in session.subagent_states.items()
            },
            "final_report": session.final_report,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
    
    def extract_session_summary(self) -> Dict[str, Any]:
        """在 cleanup 前提取当前任务的关键信息摘要（追问支持）。
        
        Returns:
            {final_report, plan, intervention_summary, roles}
        """
        summary: Dict[str, Any] = {
            "final_report": "",
            "plan": None,
            "intervention_summary": None,
            "roles": [],
        }
        
        # 从最新的 TaskSession 中提取
        current_session = None
        if self.current_task_session_id and self.current_task_session_id in self.sessions:
            current_session = self.sessions[self.current_task_session_id]
        elif self.sessions:
            # 取最后一个
            current_session = list(self.sessions.values())[-1]
        
        if current_session:
            # 最终报告
            if current_session.final_report:
                summary["final_report"] = current_session.final_report
            
            # 计划（序列化角色配置）
            if current_session.plan:
                try:
                    summary["plan"] = {
                        "analysis": current_session.plan.analysis,
                        "original_task": current_session.plan.original_task,
                    }
                except Exception:
                    pass
                
                # 角色配置列表（用于角色复用）
                roles = []
                for config in current_session.plan.subagent_configs:
                    role = config.role
                    roles.append({
                        "name": role.name,
                        "description": role.description,
                        "capabilities": role.capabilities,
                        "focus_areas": role.focus_areas,
                        "task_segment": config.task_segment,
                        "expertise_level": role.expertise_level,
                    })
                summary["roles"] = roles
        
        # 人工干预摘要
        if self.relay_coordinator.intervention_history:
            parts = []
            for intervention in self.relay_coordinator.intervention_history[-5:]:
                info = ""
                if intervention.type == InterventionType.INJECT:
                    info = intervention.payload.get("information", "")[:200]
                elif intervention.type == InterventionType.ADJUST:
                    info = str(intervention.payload.get("adjustments", {}))[:200]
                else:
                    info = intervention.reason or intervention.type.value
                parts.append(f"- [{intervention.type.value}] {info}")
            summary["intervention_summary"] = "\n".join(parts)
        
        print(f"[MasterAgent] Extracted session summary: report={len(summary['final_report'])}chars, "
              f"roles={len(summary['roles'])}, interventions={'yes' if summary['intervention_summary'] else 'no'}")
        return summary
    
    def cleanup(self):
        """
        清理资源
        
        在会话结束时调用，释放所有相关资源
        """
        print(f"[MasterAgent] Cleaning up session: {self.session_id[:8]}...")
        
        # 取消所有活跃的 Subagent
        for agent_id, subagent in list(self.active_subagents.items()):
            try:
                subagent.cancel()
            except Exception as e:
                print(f"[MasterAgent] Error cancelling subagent {agent_id[:8]}: {e}")
        
        # 清空 Subagent 注册
        for agent_id in list(self.relay_coordinator.agent_callbacks.keys()):
            self.relay_coordinator.unregister_agent(agent_id)
        
        # 清空状态
        self.active_subagents.clear()
        self.sessions.clear()
        self.pending_relay_events.clear()
        
        # 清空中继站数据
        self.relay_coordinator.stations.clear()
        self.relay_coordinator.message_history.clear()
        self.relay_coordinator.intervention_history.clear()
        
        print(f"[MasterAgent] Session {self.session_id[:8]}... cleaned up")
    
    def get_instance_info(self) -> Dict[str, Any]:
        """获取实例信息（用于调试）"""
        return {
            "session_id": self.session_id,
            "provider_type": self.provider_type,
            "model": self.model,
            "active_subagents_count": len(self.active_subagents),
            "sessions_count": len(self.sessions),
            "relay_stations_count": len(self.relay_coordinator.stations),
            "message_history_count": len(self.relay_coordinator.message_history),
            "intervention_history_count": len(self.relay_coordinator.intervention_history),
        }


# 整合系统提示词
INTEGRATION_SYSTEM_PROMPT = """你是一个专业的内容整合专家。你的任务是将多个专业角色的分析结果整合成一份完整、连贯、深入的报告。

## 当前时间
{current_time}

## 整合原则

1. **结构清晰**：使用清晰的章节结构组织内容
2. **内容融合**：不是简单堆砌，而是真正融合各角色的见解
3. **突出关键**：强调各角色发现的关键点和独特见解
4. **消除矛盾**：如果不同角色有矛盾的观点，进行分析和调和
5. **增值洞察**：基于综合信息，提供更高层次的洞察

## 输出格式

使用 Markdown 格式，包括：
- 标题和副标题
- 要点列表
- 适当的强调（粗体、斜体）
- 必要时使用表格或引用

## 引用与来源

**重要**：如果各角色的分析结果中包含了搜索引用或参考链接，你必须在报告末尾统一整理一个 **参考来源** 章节，汇总所有被引用的链接。格式如下：

```
## 参考来源
- [标题](URL)
- [标题](URL)
```

- 不要遗漏任何角色报告中出现的引用链接
- 去除重复链接
- 按主题或出现顺序排列

## 输出风格

- 专业但易读
- 逻辑严密
- 见解深刻
- 结论明确
"""
