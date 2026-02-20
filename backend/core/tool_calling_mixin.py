"""
Tool Calling Mixin for Subagent

提供 Tool Calling 能力的混入类，可被 Subagent 使用。

使用方式：
1. Subagent 初始化时加载工具处理器
2. 在 _execute_iteration 中检查 tool_calls
3. 如果有 tool_calls，执行工具并继续对话

设计考量：
- 作为独立模块，不修改原有 Subagent 代码
- 可选启用，不影响现有功能
- 支持异步工具执行
"""

import json
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class ToolCallingMixin:
    """
    Tool Calling 混入类
    
    为 Subagent 提供工具调用能力
    """
    
    def _init_tool_calling(self):
        """初始化 Tool Calling 相关属性"""
        self._tool_handler = None
        self._tool_definitions = []
        self._tool_call_history = []
        
        # 尝试加载工具处理器
        try:
            from skills.v2.tool_handler import get_global_handler, init_skill_tools
            self._tool_handler = get_global_handler()
            
            # 初始化技能工具（如果尚未初始化）
            if not self._tool_handler.list_tools():
                init_skill_tools()
            
            self._tool_definitions = self._tool_handler.get_tool_definitions()
            logger.info(f"Tool calling initialized with {len(self._tool_definitions)} tools")
            
        except ImportError as e:
            logger.warning(f"Tool calling not available: {e}")
    
    def _get_tools_for_skill(self, skill_name: str) -> List[Dict[str, Any]]:
        """获取特定技能的工具定义"""
        if not self._tool_handler:
            return []
        
        return [
            tool for tool in self._tool_definitions
            if self._tool_handler._tools.get(
                tool.get("function", {}).get("name"), {}
            ).get("skill_name") == skill_name
        ]
    
    def _get_assigned_skill_tools(self) -> List[Dict[str, Any]]:
        """获取已分配技能的工具定义"""
        if not hasattr(self, 'skill_set') or not self.skill_set:
            return []
        
        tools = []
        for skill_name in self.skill_set.list_skills():
            tools.extend(self._get_tools_for_skill(skill_name))
        
        return tools
    
    async def _execute_with_tools(
        self,
        messages: List[LLMMessage],
        max_tool_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        执行带有 Tool Calling 循环的 LLM 调用
        
        Args:
            messages: 对话消息列表
            max_tool_iterations: 最大工具调用迭代数
            
        Returns:
            {
                "content": str,  # 最终响应内容
                "tool_calls_made": List,  # 执行的工具调用记录
                "iterations": int  # 迭代次数
            }
        """
        if not self._tool_handler or not self._tool_definitions:
            # 没有工具，直接调用
            response = await self.provider.chat_complete(messages, self.llm_config)
            return {
                "content": response.get("content", ""),
                "tool_calls_made": [],
                "iterations": 1
            }
        
        tools = self._get_assigned_skill_tools()
        current_messages = list(messages)
        tool_calls_made = []
        iteration = 0
        
        while iteration < max_tool_iterations:
            iteration += 1
            
            # 调用 LLM，传入工具定义
            response = await self.provider.chat_complete(
                current_messages,
                self.llm_config,
                tools=tools
            )
            
            content = response.get("content", "")
            tool_calls = response.get("tool_calls")
            
            if not tool_calls:
                # 没有工具调用，返回响应
                return {
                    "content": content,
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration
                }
            
            logger.info(f"Tool calls received: {[tc.get('function', {}).get('name') for tc in tool_calls]}")
            
            # 记录 assistant 消息（带 tool_calls）
            current_messages.append(LLMMessage(
                role="assistant",
                content=content or "",
                tool_calls=tool_calls
            ))
            
            # 执行工具调用
            tool_results = await self._tool_handler.handle_tool_calls(tool_calls)
            
            # 记录工具执行
            for tc, result in zip(tool_calls, tool_results):
                tool_calls_made.append({
                    "call": tc,
                    "result": result
                })
            
            # 添加工具结果消息
            for result in tool_results:
                current_messages.append(LLMMessage(
                    role="tool",
                    content=result.get("content", "{}"),
                    tool_call_id=result.get("tool_call_id"),
                    name=result.get("name")
                ))
        
        # 达到最大迭代数
        logger.warning(f"Max tool iterations ({max_tool_iterations}) reached")
        return {
            "content": content,
            "tool_calls_made": tool_calls_made,
            "iterations": iteration
        }
    
    def _format_tool_results_for_prompt(self, tool_results: List[Dict[str, Any]]) -> str:
        """
        将工具结果格式化为 Prompt 文本
        
        用于不支持原生 tool message 的 LLM
        """
        if not tool_results:
            return ""
        
        parts = ["\n## 🔧 工具执行结果\n"]
        
        for item in tool_results:
            call = item.get("call", {})
            result = item.get("result", {})
            
            func_name = call.get("function", {}).get("name", "unknown")
            content = result.get("content", "{}")
            
            try:
                data = json.loads(content) if isinstance(content, str) else content
            except json.JSONDecodeError:
                data = {"raw": content}
            
            parts.append(f"### {func_name}")
            
            if data.get("success"):
                parts.append("**状态**: ✅ 成功")
                
                if "results" in data:
                    parts.append(f"**结果数量**: {len(data['results'])}\n")
                    for i, res in enumerate(data["results"][:5], 1):
                        title = res.get("title", "无标题")
                        url = res.get("url", "")
                        snippet = res.get("snippet", "")[:200]
                        parts.append(f"**{i}. {title}**")
                        if url:
                            parts.append(f"   链接: {url}")
                        if snippet:
                            parts.append(f"   摘要: {snippet}")
                        parts.append("")
                elif "count" in data:
                    parts.append(f"**记录数**: {data['count']}")
                else:
                    # 输出 JSON
                    parts.append(f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```")
            else:
                parts.append(f"**状态**: ❌ 失败")
                parts.append(f"**错误**: {data.get('error', 'Unknown error')}")
            
            parts.append("")
        
        return "\n".join(parts)


def enable_tool_calling(subagent_instance):
    """
    为 Subagent 实例启用 Tool Calling 能力
    
    使用方式：
    ```python
    from core.tool_calling_mixin import enable_tool_calling
    
    subagent = SubagentRuntime(config)
    enable_tool_calling(subagent)
    
    # 现在可以使用 tool calling
    result = await subagent._execute_with_tools(messages)
    ```
    """
    # 动态添加方法
    import types
    
    mixin = ToolCallingMixin()
    
    subagent_instance._init_tool_calling = types.MethodType(
        mixin._init_tool_calling.__func__, subagent_instance
    )
    subagent_instance._get_tools_for_skill = types.MethodType(
        mixin._get_tools_for_skill.__func__, subagent_instance
    )
    subagent_instance._get_assigned_skill_tools = types.MethodType(
        mixin._get_assigned_skill_tools.__func__, subagent_instance
    )
    subagent_instance._execute_with_tools = types.MethodType(
        mixin._execute_with_tools.__func__, subagent_instance
    )
    subagent_instance._format_tool_results_for_prompt = types.MethodType(
        mixin._format_tool_results_for_prompt.__func__, subagent_instance
    )
    
    # 初始化
    subagent_instance._init_tool_calling()
    
    return subagent_instance


__all__ = [
    "ToolCallingMixin",
    "enable_tool_calling",
]
