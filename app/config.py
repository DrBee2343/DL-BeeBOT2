from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    webhook_secret: str
    base_url: str
    database_url: str
    redis_url: str

    admin_ids: str = ""
    data_dir: str = "/data"

    free_generations: int = 2
    default_validity_years: int = 3
    render_timeout_s: int = 40
    max_concurrent_renders: int = 2
    render_cost: int = 1

    paystack_secret_key: str = ""
    crypto_usdt_bsc_address: str = ""
    crypto_usdc_base_address: str = ""

    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("redis_url")
    @classmethod
    def _redis_scheme(cls, value: str) -> str:
        if value.startswith("redis://") or value.startswith("rediss://"):
            return value
        raise ValueError("REDIS_URL must start with redis:// or rediss://")

    @property
    def admins(self) -> set[int]:
        return {int(x) for x in self.admin_ids.replace(" ", "").split(",") if x}

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret}"

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.webhook_path}"

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def render_path(self) -> Path:
        path = self.data_path / "renders"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
