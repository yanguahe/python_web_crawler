"""
Application configuration settings.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Settings
    app_name: str = "arXiv Paper Crawler"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # arXiv API Settings
    arxiv_api_base_url: str = "https://export.arxiv.org/api/query"
    arxiv_max_results: int = 10
    arxiv_rate_limit_delay: float = 3.0  # seconds between requests
    
    # DeepSeek API Settings
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-reasoner"
    deepseek_max_tokens: int = 65536  # 64K - DeepSeek max supported
    
    # Storage Settings
    data_dir: str = "data/papers"
    
    # Base directory (project root)
    base_dir: Path = Path(__file__).resolve().parent.parent
    
    @property
    def papers_dir(self) -> Path:
        """Get the absolute path to the papers directory."""
        return self.base_dir / self.data_dir
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

