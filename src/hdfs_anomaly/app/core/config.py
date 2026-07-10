from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HDFS Log Anomaly Detection API"
    debug: bool = False
    sql_echo: bool = False

    database_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60

    bootstrap_admin_enabled: bool = False
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    demo_user_enabled: bool = False
    demo_email: str | None = None
    demo_password: str | None = None

    backend_cors_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if not self.backend_cors_origins:
            return []

        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
