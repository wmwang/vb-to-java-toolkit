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
from pathlib import Path
from datetime import datetime
import json
import os


def _get_log_dir() -> Path:
    """
    取得 log 目錄（專案目錄下的 logs/）
    
    優先順序：
    1. 環境變數 VB_TOOLKIT_LOG_DIR
    2. 專案目錄下的 logs/
    """
    env_dir = os.environ.get("VB_TOOLKIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    
    # 預設：專案目錄下的 logs/
    return Path(__file__).parent.parent.parent / "logs"


# Debug Log 目錄
DEBUG_LOG_DIR = _get_log_dir()
DEBUG_LOG_FILE = DEBUG_LOG_DIR / "llm_debug.log"


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4000
    debug: bool = True  # 是否啟用 debug logging


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
        
        # 初始化 debug log
        if self.config.debug:
            self._init_debug_log()
    
    def _init_debug_log(self):
        """初始化 debug log 目錄"""
        DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _log_request(self, system_prompt: str, user_prompt: str):
        """記錄請求到 debug log"""
        if not self.config.debug:
            return
        
        # 使用更易讀的純文字格式，顯示實際送出的 messages
        log_text = f"""
================================================================================
[REQUEST] {datetime.now().isoformat()}
================================================================================
Model: {self.config.model}
Base URL: {self.config.base_url}
Temperature: {self.config.temperature}
Max Tokens: {self.config.max_tokens}

--- Messages (實際送出格式) ---

[System]
{system_prompt}

[User]
{user_prompt}
"""
        self._write_log_text(log_text)
    
    def _log_response(self, response: str, tokens_estimated: int):
        """記錄回應到 debug log"""
        if not self.config.debug:
            return
        
        log_text = f"""
================================================================================
[RESPONSE] {datetime.now().isoformat()}
================================================================================
Response Length: {len(response)} chars
Tokens (estimated): {tokens_estimated}

[Assistant]
{response}
"""
        self._write_log_text(log_text)
    
    def _log_error(self, error: Exception):
        """記錄錯誤到 debug log"""
        if not self.config.debug:
            return
        
        log_text = f"""
================================================================================
[ERROR] {datetime.now().isoformat()}
================================================================================
Error Type: {type(error).__name__}
Error Message: {str(error)}
"""
        self._write_log_text(log_text)
    
    def _write_log_text(self, log_text: str):
        """寫入 log 檔案（純文字格式）"""
        try:
            with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_text)
        except Exception:
            pass  # 忽略 log 寫入錯誤
    
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
        # 記錄請求
        self._log_request(system_prompt, user_prompt)
        
        # 強制格式：只有 System + User
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
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
            tokens_estimated = (len(user_prompt) + len(system_prompt) + len(full_response)) // 4
            self.total_tokens_used += tokens_estimated
            
            # 記錄回應
            self._log_response(full_response, tokens_estimated)
            
            return full_response
        
        except Exception as e:
            self._log_error(e)
            raise
    
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
        # 記錄請求
        self._log_request(system_prompt, user_prompt)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        collected_content = []
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_content.append(content)
                    yield content
            
            # 記錄完整回應
            full_response = "".join(collected_content)
            tokens_estimated = (len(user_prompt) + len(system_prompt) + len(full_response)) // 4
            self._log_response(full_response, tokens_estimated)
        
        except Exception as e:
            self._log_error(e)
            raise
    
    def get_token_usage(self) -> int:
        """取得已使用的 Token 數量（估算值）"""
        return self.total_tokens_used
    
    @staticmethod
    def get_debug_log_path() -> Path:
        """取得 debug log 檔案路徑"""
        return DEBUG_LOG_FILE
    
    @staticmethod
    def clear_debug_log():
        """清除 debug log"""
        if DEBUG_LOG_FILE.exists():
            DEBUG_LOG_FILE.unlink()


def create_llm_client(
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    debug: bool = True,
) -> LLMClient:
    """
    建立 LLM Client 的便捷函數
    
    Args:
        api_key: OpenAI API Key
        base_url: API Endpoint（預設 https://api.openai.com/v1）
        model: 模型名稱
        debug: 是否啟用 debug logging（預設 True）
        
    Returns:
        LLMClient 實例
    """
    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        debug=debug,
    )
    return LLMClient(config)
