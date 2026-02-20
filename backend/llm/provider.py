"""
LLM Provider - 统一的 LLM 接口抽象

支持 OpenAI 和 Claude API
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict, Any
from pydantic import BaseModel
import os


class LLMMessage(BaseModel):
    """LLM 消息"""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_api_dict(self) -> Dict[str, Any]:
        """序列化为 API 请求格式，处理空 content 兼容性问题。
        
        Claude API 不允许 assistant 消息同时有 tool_calls 和空 content，
        此方法确保这种情况下 content 字段被排除。
        """
        d = self.model_dump(exclude_none=True)
        # assistant 消息有 tool_calls 时，空 content 会导致 Claude 报错
        if self.role == "assistant" and self.tool_calls and not self.content:
            d.pop("content", None)
        return d


class LLMConfig(BaseModel):
    """LLM 配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 16384  # 增大到 16K，支持复杂输出
    top_p: Optional[float] = None  # 默认不设置，避免与 temperature 冲突
    stream: bool = True


class LLMProvider(ABC):
    """LLM 提供者抽象基类"""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        pass
    
    @abstractmethod
    async def chat_complete(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """非流式聊天，返回完整响应"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI Provider"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL")
        )
    
    async def chat(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        request_params = {
            "model": config.model,
            "messages": [m.to_api_dict() for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": True,
        }
        
        # 只有明确设置了 top_p 时才传递，避免与 temperature 冲突
        if config.top_p is not None:
            request_params["top_p"] = config.top_p
        
        if tools:
            request_params["tools"] = tools
        
        stream = await self.client.chat.completions.create(**request_params)
        
        async for chunk in stream:
            # 检查 choices 是否为空
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
    
    async def chat_complete(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """非流式聊天"""
        request_params = {
            "model": config.model,
            "messages": [m.to_api_dict() for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": False,
        }
        
        # 只有明确设置了 top_p 时才传递，避免与 temperature 冲突
        if config.top_p is not None:
            request_params["top_p"] = config.top_p
        
        if tools:
            request_params["tools"] = tools
        
        print(f"[OpenAIProvider] chat_complete request: model={config.model}, temp={config.temperature}")
        
        try:
            response = await self.client.chat.completions.create(**request_params)
            print(f"[OpenAIProvider] Got response, choices count: {len(response.choices) if response.choices else 0}")
        except Exception as e:
            print(f"[OpenAIProvider] API Error: {type(e).__name__}: {e}")
            raise
        
        # 检查 choices 是否有效
        if not response.choices or len(response.choices) == 0:
            print(f"[OpenAIProvider] Warning: No choices in response!")
            return {
                "content": "",
                "tool_calls": None,
                "finish_reason": "error"
            }
        
        message = response.choices[0].message
        content = message.content or ""
        print(f"[OpenAIProvider] Response content length: {len(content)}")
        
        result = {
            "content": content,
            "tool_calls": None,
            "finish_reason": response.choices[0].finish_reason
        }
        
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return result


class ClaudeProvider(LLMProvider):
    """Claude Provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
    
    async def chat(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        # 提取 system message
        system_content = ""
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        request_params = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "messages": chat_messages,
        }
        
        if system_content:
            request_params["system"] = system_content
        
        if tools:
            # 转换 OpenAI 格式的 tools 到 Claude 格式
            claude_tools = self._convert_tools(tools)
            request_params["tools"] = claude_tools
        
        async with self.client.messages.stream(**request_params) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def chat_complete(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """非流式聊天"""
        # 提取 system message
        system_content = ""
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        request_params = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "messages": chat_messages,
        }
        
        if system_content:
            request_params["system"] = system_content
        
        if tools:
            claude_tools = self._convert_tools(tools)
            request_params["tools"] = claude_tools
        
        response = await self.client.messages.create(**request_params)
        
        result = {
            "content": "",
            "tool_calls": None,
            "finish_reason": response.stop_reason
        }
        
        for block in response.content:
            if block.type == "text":
                result["content"] = block.text
            elif block.type == "tool_use":
                if result["tool_calls"] is None:
                    result["tool_calls"] = []
                result["tool_calls"].append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": str(block.input)
                    }
                })
        
        return result
    
    def _convert_tools(self, openai_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将 OpenAI 格式的 tools 转换为 Claude 格式"""
        claude_tools = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool["function"]
                claude_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
        return claude_tools


class LLMProviderFactory:
    """LLM Provider 工厂"""
    
    _providers: Dict[str, LLMProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_type: str = "openai") -> LLMProvider:
        """获取 LLM Provider"""
        if provider_type not in cls._providers:
            if provider_type == "openai":
                cls._providers[provider_type] = OpenAIProvider()
            elif provider_type == "claude":
                cls._providers[provider_type] = ClaudeProvider()
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")
        
        return cls._providers[provider_type]
    
    @classmethod
    def get_default_config(cls, provider_type: str = "openai") -> LLMConfig:
        """获取默认配置"""
        if provider_type == "openai":
            # 使用兼容性更好的模型名称
            return LLMConfig(model=os.getenv("OPENAI_MODEL", "gpt-4o"))
        elif provider_type == "claude":
            return LLMConfig(model=os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229"))
        else:
            return LLMConfig(model="gpt-4o")
