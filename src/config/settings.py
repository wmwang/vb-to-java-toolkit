"""設定模組"""

from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """應用程式設定"""
    
    # LLM 設定
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    
    # 路徑設定
    data_dir: Path = Path("./data")
    vector_db_path: Path = Path("./data/vectordb")
    
    # 分析設定
    max_batch_size: int = 10
    rate_limit_per_minute: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_data_dir(self, subdir: str = "") -> Path:
        """取得資料目錄路徑"""
        path = self.data_dir / subdir if subdir else self.data_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    """取得快取的設定實例"""
    return Settings()
