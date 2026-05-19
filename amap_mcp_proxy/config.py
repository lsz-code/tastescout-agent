from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AMAP_MCP_URL: str
    MCP_TIMEOUT_SECONDS: int = 15

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
