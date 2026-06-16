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
    # State income tax is intentionally opt-in: a single flat rate cannot model
    # 40+ state systems honestly, so it stays 0 unless explicitly configured.
    default_state_tax_rate: float = 0.0
    # E-file boundary: no public IRS API exists. "pdf" produces a self-file
    # package; "mock_transmitter" simulates a commercial MeF transmitter.
    efile_backend: str = "pdf"
    # W-2 extractor: "label" (offline parser) or "azure" (Document Intelligence).
    w2_extractor: str = "label"
    azure_di_endpoint: str = ""
    azure_di_key: str = ""
    tesseract_cmd: str | None = None
    allowed_origins: str = "http://localhost:5173"
    # API key for write/read endpoints; empty disables auth (local dev only).
    api_key: str = ""
    log_level: str = "INFO"

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
