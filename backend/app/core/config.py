from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "TasteScout Agent"
    APP_ENV: str = "dev"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "tastescout"
    POSTGRES_PASSWORD: str = "tastescout"
    POSTGRES_DB: str = "tastescout"
    DATABASE_URL: str = ""

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str | None = None
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "qwen-plus"
    LLM_TIMEOUT_SECONDS: int = 30
    AGENT_TOOL_MODE: str = "function_calling"

    AMAP_MCP_PROXY_URL: str = "http://127.0.0.1:8010"
    MCP_TIMEOUT_SECONDS: int = 15

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    @model_validator(mode="after")
    def build_connection_urls(self) -> "Settings":
        print("Building connection URLs...")
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                "postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.REDIS_URL:
            self.REDIS_URL = (
                f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env.example",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
