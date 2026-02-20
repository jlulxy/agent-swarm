"""
中继站 (Relay Station)

核心设计：
1. 集中式协调 - Master Agent 收集所有信息，统一分发
2. 自适应触发 - Agent 自己判断何时需要中继
3. 3D 编排 - 支持多阶段、多维度的信息交换

中继站是 Agent 间协作的"枢纽"，它让 Agent 能够：
- 交换关键发现
- 互相校准认知
- 协调行动方向
"""

import asyncio
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
import uuid

from core.models import (
    RelayStation as RelayStationModel,
    RelayMessage,
    RelayType,
    SubagentState,
    AgentStatus,
    HumanIntervention,
    InterventionType,
    InterventionScope,
)


class RelayStationCoordinator:
    """中继站协调器 - 管理所有中继站
    
    重要：每个 RelayStationCoordinator 实例对应一个独立的会话
    不同会话的中继站、消息历史、干预历史完全隔离
    """
    
    def __init__(
        self,
        on_station_opened: Optional[Callable[[RelayStationModel], None]] = None,
        on_message_broadcast: Optional[Callable[[str, RelayMessage], None]] = None,
        on_station_closed: Optional[Callable[[RelayStationModel, str], None]] = None,
        on_intervention_broadcast: Optional[Callable[[str, RelayMessage, HumanIntervention], None]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Args:
            on_station_opened: 中继站开启回调
            on_message_broadcast: 消息广播回调
            on_station_closed: 中继站关闭回调
            on_intervention_broadcast: 人工干预广播回调
            session_id: 所属会话 ID（用于日志和调试）
        """
        self.session_id = session_id or "unknown"
        
        # 本会话专属的中继站
        self.stations: Dict[str, RelayStationModel] = {}
        self.active_station_id: Optional[str] = None
        
        # 本会话专属的消息历史
        self.message_history: List[RelayMessage] = []
        
        # 本会话专属的人工干预历史
        self.intervention_history: List[HumanIntervention] = []
        
        # 回调
        self.on_station_opened = on_station_opened
        self.on_message_broadcast = on_message_broadcast
        self.on_station_closed = on_station_closed
        self.on_intervention_broadcast = on_intervention_broadcast
        
        # 本会话专属的 Agent 引用（用于发送消息）
        self.agent_callbacks: Dict[str, Callable[[RelayMessage], None]] = {}
        
        # 本会话专属的 Agent 干预响应回调
        self.agent_intervention_handlers: Dict[str, Callable[[RelayMessage, HumanIntervention], None]] = {}
        
        print(f"[RelayStation:{self.session_id[:8]}] Coordinator initialized")
    
    def register_agent(self, agent_id: str, callback: Callable[[RelayMessage], None], intervention_handler: Optional[Callable[[RelayMessage, HumanIntervention], None]] = None):
        """注册 Agent 的消息接收回调
        
        Args:
            agent_id: Agent ID
            callback: 普通中继消息回调
            intervention_handler: 人工干预消息特殊处理回调（可选）
        """
        self.agent_callbacks[agent_id] = callback
        if intervention_handler:
            self.agent_intervention_handlers[agent_id] = intervention_handler
    
    def unregister_agent(self, agent_id: str):
        """注销 Agent"""
        self.agent_callbacks.pop(agent_id, None)
        self.agent_intervention_handlers.pop(agent_id, None)
    
    def create_station(
        self,
        name: str,
        phase: int,
        participating_agents: List[str]
    ) -> RelayStationModel:
        """创建中继站"""
        station = RelayStationModel(
            id=str(uuid.uuid4()),
            name=name,
            phase=phase,
            participating_agents=participating_agents,
            messages=[],
            is_active=False,
        )
        self.stations[station.id] = station
        return station
    
    async def open_station(self, station_id: str) -> bool:
        """开启中继站"""
        if station_id not in self.stations:
            return False
        
        # 关闭当前活跃的中继站
        if self.active_station_id:
            await self.close_station(self.active_station_id)
        
        station = self.stations[station_id]
        station.is_active = True
        station.started_at = datetime.now()
        self.active_station_id = station_id
        
        if self.on_station_opened:
            self.on_station_opened(station)
        
        return True
    
    async def close_station(self, station_id: str) -> Optional[str]:
        """关闭中继站，返回汇总信息"""
        if station_id not in self.stations:
            return None
        
        station = self.stations[station_id]
        station.is_active = False
        station.completed_at = datetime.now()
        
        if self.active_station_id == station_id:
            self.active_station_id = None
        
        # 生成汇总
        summary = self._generate_station_summary(station)
        
        if self.on_station_closed:
            self.on_station_closed(station, summary)
        
        return summary
    
    async def broadcast_message(
        self,
        message: RelayMessage,
        station_id: Optional[str] = None
    ):
        """广播中继消息"""
        # 确定目标中继站：指定站 > 活跃站 > 已存在的任意站
        target_station_id = station_id or self.active_station_id
        if not target_station_id and self.stations:
            # 使用已存在的第一个活跃站或最后一个站
            active_stations = [sid for sid, s in self.stations.items() if s.is_active]
            target_station_id = active_stations[0] if active_stations else list(self.stations.keys())[-1]
        
        # 记录中继站 ID 到元数据
        if target_station_id:
            message.metadata["station_id"] = target_station_id
        
        if target_station_id and target_station_id in self.stations:
            station = self.stations[target_station_id]
            station.messages.append(message)
            print(f"[RelayStation] Message added to station '{station.name}' ({target_station_id})")
        else:
            print(f"[RelayStation] Warning: No station found, message only in history")
        
        self.message_history.append(message)
        
        # 确定目标 Agent
        target_ids = message.target_agent_ids
        if not target_ids:
            # 广播给所有 Agent（除了发送者）
            target_ids = [
                aid for aid in self.agent_callbacks.keys()
                if aid != message.source_agent_id
            ]
        
        # 发送消息
        for agent_id in target_ids:
            if agent_id in self.agent_callbacks:
                callback = self.agent_callbacks[agent_id]
                await self._safe_callback(callback, message)
        
        if self.on_message_broadcast:
            self.on_message_broadcast(target_station_id or "", message)
    
    async def broadcast_intervention(
        self,
        intervention: HumanIntervention,
        station_id: Optional[str] = None
    ) -> RelayMessage:
        """
        广播人工干预消息到中继站
        
        这是升级后的核心功能：人工干预不再只是直接注入到单个 Agent，
        而是通过中继站广播，让所有相关 Agent 都能感知并做出响应。
        
        Args:
            intervention: 人工干预对象
            station_id: 目标中继站ID（默认使用活跃站）
        
        Returns:
            生成的中继消息
        """
        # 优先使用指定的站点，否则使用活跃站，否则使用任意存在的站
        target_station_id = station_id or self.active_station_id
        if not target_station_id and self.stations:
            # 使用最后创建的站点
            target_station_id = list(self.stations.keys())[-1]
        
        # 记录干预历史
        self.intervention_history.append(intervention)
        
        # 构建中继消息内容
        content_parts = [
            f"🚨 **人工干预通知**",
            f"",
            f"**干预类型**: {intervention.type.value}",
            f"**作用范围**: {intervention.scope.value}",
            f"**优先级**: {intervention.priority}/10",
        ]
        
        if intervention.reason:
            content_parts.append(f"**干预原因**: {intervention.reason}")
        
        # 根据干预类型添加具体指令
        if intervention.type == InterventionType.INJECT:
            inject_content = intervention.payload.get("information", "")
            content_parts.extend([
                f"",
                f"**注入信息**:",
                inject_content
            ])
        elif intervention.type == InterventionType.ADJUST:
            adjustments = intervention.payload.get("adjustments", {})
            content_parts.append(f"")
            content_parts.append(f"**调整指令**:")
            for key, value in adjustments.items():
                content_parts.append(f"- {key}: {value}")
        elif intervention.type == InterventionType.PAUSE:
            content_parts.append(f"")
            content_parts.append(f"**指令**: 暂停当前工作，等待进一步指示")
        elif intervention.type == InterventionType.RESUME:
            content_parts.append(f"")
            content_parts.append(f"**指令**: 恢复工作，继续之前的任务")
        elif intervention.type == InterventionType.CANCEL:
            content_parts.append(f"")
            content_parts.append(f"**指令**: 取消当前任务")
        elif intervention.type == InterventionType.RESTART:
            content_parts.append(f"")
            content_parts.append(f"**指令**: 重新开始任务")
        
        # 确定目标 Agent
        target_ids = []
        if intervention.scope == InterventionScope.SINGLE and intervention.target_agent_id:
            target_ids = [intervention.target_agent_id]
        elif intervention.scope == InterventionScope.SELECTED and intervention.target_agent_ids:
            target_ids = intervention.target_agent_ids
        elif intervention.scope in [InterventionScope.ALL, InterventionScope.BROADCAST]:
            target_ids = []  # 空列表表示广播给所有 Agent
        
        # 创建中继消息
        relay_message = RelayMessage(
            type=RelayType.HUMAN_INTERVENTION,
            source_agent_id="human",
            source_agent_name="🧑‍💼 人类操作员",
            target_agent_ids=target_ids,
            content="\n".join(content_parts),
            importance=min(1.0, intervention.priority / 10 + 0.3),  # 人工干预重要性高
            metadata={
                "intervention_id": intervention.id,
                "intervention_type": intervention.type.value,
                "scope": intervention.scope.value,
                "priority": intervention.priority,
                "payload": intervention.payload,
                "requires_acknowledgement": True,
                "station_id": target_station_id or "",
            }
        )
        
        # 添加到中继站消息历史
        if target_station_id and target_station_id in self.stations:
            station = self.stations[target_station_id]
            station.messages.append(relay_message)
            print(f"[RelayStation] Added intervention message to station {target_station_id}")
        else:
            print(f"[RelayStation] No active station, message only in history. Target ID: {target_station_id}")
        
        self.message_history.append(relay_message)
        
        # 确定实际接收者
        actual_targets = target_ids if target_ids else list(self.agent_callbacks.keys())
        print(f"[RelayStation] Broadcasting to {len(actual_targets)} agents: {actual_targets}")
        
        # 发送给目标 Agent
        for agent_id in actual_targets:
            if agent_id in self.agent_callbacks:
                callback = self.agent_callbacks[agent_id]
                
                # 如果有专门的干预处理器，使用它
                if agent_id in self.agent_intervention_handlers:
                    handler = self.agent_intervention_handlers[agent_id]
                    await self._safe_intervention_callback(handler, relay_message, intervention)
                    print(f"[RelayStation] Sent intervention to {agent_id} via intervention_handler")
                else:
                    # 使用普通回调
                    await self._safe_callback(callback, relay_message)
                    print(f"[RelayStation] Sent intervention to {agent_id} via normal callback")
            else:
                print(f"[RelayStation] Warning: Agent {agent_id} not registered!")
        
        # 触发干预广播回调（用于前端通知）
        # 注意：只使用一个回调，避免重复触发
        if self.on_intervention_broadcast:
            self.on_intervention_broadcast(target_station_id or "", relay_message, intervention)
        elif self.on_message_broadcast:
            # 只有当没有专门的干预回调时才用普通回调
            self.on_message_broadcast(target_station_id or "", relay_message)
        
        return relay_message
    
    async def _safe_intervention_callback(
        self, 
        handler: Callable, 
        message: RelayMessage, 
        intervention: HumanIntervention
    ):
        """安全执行干预回调"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message, intervention)
            else:
                handler(message, intervention)
        except Exception as e:
            print(f"Intervention callback error: {e}")
    
    async def request_alignment(
        self,
        requesting_agent_id: str,
        requesting_agent_name: str,
        reason: str,
        current_understanding: str
    ) -> List[RelayMessage]:
        """
        请求对齐 - Agent 请求与其他 Agent 对齐认知
        
        这是 3D 编排的关键：Agent 主动触发同步点
        """
        # 创建对齐请求消息
        alignment_request = RelayMessage(
            type=RelayType.ALIGNMENT,
            source_agent_id=requesting_agent_id,
            source_agent_name=requesting_agent_name,
            target_agent_ids=[],  # 广播
            content=f"请求对齐：{reason}\n\n当前理解：{current_understanding}",
            importance=0.9,
            metadata={"reason": reason}
        )
        
        await self.broadcast_message(alignment_request)
        
        # 注意：不再阻塞等待，响应会通过异步回调机制处理
        # 其他 Agent 收到请求后会主动发送响应消息
        
        # 返回相关的消息历史
        return [
            msg for msg in self.message_history
            if msg.type == RelayType.ALIGNMENT or msg.type.value.startswith("alignment")
        ]
    
    async def checkpoint(
        self,
        agent_states: Dict[str, SubagentState],
        phase: int
    ) -> Dict[str, any]:
        """
        检查点 - 阶段性同步
        
        收集所有 Agent 的当前状态，进行汇总和校准
        """
        checkpoint_summary = {
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "discoveries": [],
            "alignment_needed": False,
        }
        
        for agent_id, state in agent_states.items():
            checkpoint_summary["agents"][agent_id] = {
                "name": state.config.role.name,
                "status": state.status.value,
                "progress": state.progress,
                "partial_result": state.partial_result[:500] if state.partial_result else "",
            }
            
            # 收集关键发现
            for msg in state.relay_messages_sent:
                if msg.get("type") == RelayType.DISCOVERY.value:
                    checkpoint_summary["discoveries"].append({
                        "agent": state.config.role.name,
                        "content": msg.get("content", "")[:200]
                    })
        
        # 检查是否需要对齐（例如，进度差异过大）
        progresses = [s["progress"] for s in checkpoint_summary["agents"].values()]
        if progresses:
            progress_diff = max(progresses) - min(progresses)
            if progress_diff > 30:
                checkpoint_summary["alignment_needed"] = True
        
        # 广播检查点消息
        checkpoint_msg = RelayMessage(
            type=RelayType.CHECKPOINT,
            source_agent_id="master",
            source_agent_name="Master Agent",
            target_agent_ids=[],
            content=f"阶段 {phase} 检查点:\n已完成 Agent 进度汇总\n发现 {len(checkpoint_summary['discoveries'])} 个关键点",
            importance=0.7,
            metadata=checkpoint_summary
        )
        
        await self.broadcast_message(checkpoint_msg)
        
        return checkpoint_summary
    
    def _generate_station_summary(self, station: RelayStationModel) -> str:
        """生成中继站汇总"""
        summary_parts = [
            f"## 中继站: {station.name} (阶段 {station.phase})",
            f"持续时间: {self._calculate_duration(station)}",
            f"消息数量: {len(station.messages)}",
            "",
        ]
        
        # 统计人工干预
        intervention_count = sum(
            1 for msg in station.messages 
            if msg.type == RelayType.HUMAN_INTERVENTION
        )
        if intervention_count > 0:
            summary_parts.append(f"人工干预次数: {intervention_count}")
            summary_parts.append("")
        
        summary_parts.append("### 关键信息交换:")
        
        for msg in station.messages:
            importance_star = "⭐" if msg.importance > 0.7 else ""
            intervention_mark = "🚨" if msg.type == RelayType.HUMAN_INTERVENTION else ""
            summary_parts.append(
                f"- {intervention_mark}[{msg.type.value}] {msg.source_agent_name}: {msg.content[:100]}... {importance_star}"
            )
        
        return "\n".join(summary_parts)
    
    def get_intervention_history(self, limit: int = 10) -> List[HumanIntervention]:
        """获取最近的人工干预历史"""
        return self.intervention_history[-limit:]
    
    def get_intervention_messages(self, station_id: Optional[str] = None) -> List[RelayMessage]:
        """获取人工干预相关的中继消息"""
        messages = self.message_history
        if station_id and station_id in self.stations:
            messages = self.stations[station_id].messages
        
        return [
            msg for msg in messages 
            if msg.type == RelayType.HUMAN_INTERVENTION
        ]
    
    def _calculate_duration(self, station: RelayStationModel) -> str:
        """计算中继站持续时间"""
        if station.started_at and station.completed_at:
            duration = (station.completed_at - station.started_at).total_seconds()
            return f"{duration:.1f}秒"
        return "进行中"
    
    async def _safe_callback(self, callback: Callable, message: RelayMessage):
        """安全执行回调"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
        except Exception as e:
            print(f"Relay callback error: {e}")


class AdaptiveRelayTrigger:
    """
    自适应中继触发器
    
    Agent 自己判断何时需要中继，而不是固定的时间点
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        Args:
            threshold: 触发阈值 (0-1)，越高表示越保守
        """
        self.threshold = threshold
        self.trigger_history: List[Dict] = []
    
    def should_trigger(
        self,
        agent_state: SubagentState,
        response_content: str,
    ) -> tuple[bool, Optional[RelayType], str]:
        """
        判断是否应该触发中继
        
        Returns:
            (should_trigger, relay_type, reason)
        """
        # 规则1: 显式请求
        if "[请求中继" in response_content:
            return True, RelayType.ALIGNMENT, "显式请求中继"
        
        # 规则2: 关键发现
        if "[关键发现]" in response_content:
            return True, RelayType.DISCOVERY, "发现关键信息"
        
        # 规则3: 检测到与其他 Agent 可能相关的内容
        cross_domain_keywords = [
            "这与", "可能与", "需要确认", "有关联",
            "建议", "假设", "推测", "可能影响"
        ]
        for keyword in cross_domain_keywords:
            if keyword in response_content:
                return True, RelayType.ALIGNMENT, f"检测到跨域相关内容: {keyword}"
        
        # 规则4: 不确定性高
        uncertainty_keywords = ["不确定", "可能", "也许", "有待验证", "需要更多信息"]
        uncertainty_count = sum(1 for k in uncertainty_keywords if k in response_content)
        if uncertainty_count >= 2:
            return True, RelayType.ALIGNMENT, "检测到高不确定性"
        
        # 规则5: 进度到达关键节点
        progress_thresholds = [25, 50, 75]
        for threshold in progress_thresholds:
            if (
                agent_state.progress >= threshold and
                not self._has_triggered_at_progress(agent_state.id, threshold)
            ):
                self._record_trigger(agent_state.id, threshold)
                return True, RelayType.CHECKPOINT, f"到达进度节点 {threshold}%"
        
        return False, None, ""
    
    def _has_triggered_at_progress(self, agent_id: str, progress: float) -> bool:
        """检查是否已在该进度点触发过"""
        for record in self.trigger_history:
            if (
                record["agent_id"] == agent_id and
                record["progress"] == progress
            ):
                return True
        return False
    
    def _record_trigger(self, agent_id: str, progress: float):
        """记录触发"""
        self.trigger_history.append({
            "agent_id": agent_id,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
