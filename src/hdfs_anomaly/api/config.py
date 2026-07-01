from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_secret_key: str
    api_jwt_algorithm: str = "HS256"
    api_access_token_expire_minutes: int = 60
    api_admin_username: str
    api_admin_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
