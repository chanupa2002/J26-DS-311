"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    supabase_url: str = ""
    supabase_key: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        configured = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # The local Vite server may be opened by either hostname. Browsers treat
        # localhost and 127.0.0.1 as distinct origins, even on the same machine.
        return list(dict.fromkeys([*configured, "http://localhost:5173", "http://127.0.0.1:5173"]))


settings = Settings()
