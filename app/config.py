from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    webhook_secret: str
    base_url: str
    database_url: str
    redis_url: str
    admin_ids: str = ""
    paystack_secret_key: str = ""
    free_generations: int = 2
    max_retries: int = 2
    render_timeout_s: int = 25

    @property
    def admins(self) -> set[int]:
        return {int(x) for x in self.admin_ids.replace(" ", "").split(",") if x}

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret}"

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
