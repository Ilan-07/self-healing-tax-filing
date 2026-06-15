from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Self-Healing Tax Filing System"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./tax_filing.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llama3.2-vision:latest"
    ollama_coder_model: str = "qwen2.5-coder:7b"
    chroma_path: Path = Path("../storage/chroma")
    storage_root: Path = Path("../storage")
    verification_threshold: float = 0.95
    max_remediation_attempts: int = 2
    default_state_tax_rate: float = 0.05
    tesseract_cmd: str | None = None
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
