"""
LLM Client 模組 - 嚴格遵循公司規範

規範要求：
1. 使用 OpenAI SDK
2. 必須使用 SSE 協定 (stream=True)
3. Prompt 格式只能使用 [System, User] messages
"""

from typing import AsyncGenerator, Optional, Callable
from openai import AsyncOpenAI
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4000


class LLMClient:
    """
    LLM Client - 公司規範版本
    
    強制規則：
    - 必須使用 SSE Streaming (stream=True)
    - 只允許 System + User message 格式
    """
    
    def __init__(self, config: LLMConfig):
        """
        初始化 LLM Client
        
        Args:
            config: LLM 配置（api_key + base_url + model）
        """
        self.config = config
        
        # 確保 URL 正確
        base_url = config.base_url
        if "/v1" not in base_url and "openai.com" in base_url:
            base_url = f"{base_url}/v1"
        
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=base_url
        )
        self.total_tokens_used = 0
    
    async def generate(
        self,
        user_prompt: str,
        system_prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        生成回應（強制使用 SSE Streaming）
        
        Args:
            user_prompt: 使用者訊息
            system_prompt: 系統訊息
            on_chunk: 可選的回調函數，每收到一個 chunk 就呼叫
            
        Returns:
            完整的回應文字
        """
        # 強制格式：只有 System + User
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # 強制使用 SSE Streaming
        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,  # 強制 SSE
        )
        
        collected_content = []
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                collected_content.append(content)
                
                # 呼叫回調（如果有提供）
                if on_chunk:
                    on_chunk(content)
        
        full_response = "".join(collected_content)
        
        # 粗略估算 Token（Streaming 模式無法取得精確 usage）
        self.total_tokens_used += (len(user_prompt) + len(system_prompt) + len(full_response)) // 4
        
        return full_response
    
    async def generate_stream(
        self,
        user_prompt: str,
        system_prompt: str,
    ) -> AsyncGenerator[str, None]:
        """
        生成回應的串流版本（產生器形式）
        
        Args:
            user_prompt: 使用者訊息
            system_prompt: 系統訊息
            
        Yields:
            每個 chunk 的文字
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def get_token_usage(self) -> int:
        """取得已使用的 Token 數量（估算值）"""
        return self.total_tokens_used


def create_llm_client(
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> LLMClient:
    """
    建立 LLM Client 的便捷函數
    
    Args:
        api_key: OpenAI API Key
        base_url: API Endpoint（預設 https://api.openai.com/v1）
        model: 模型名稱
        
    Returns:
        LLMClient 實例
    """
    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    return LLMClient(config)
