from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "centraldevice"
    secret_key: str = "change-me-in-production"
    vault_key: str = ""
    access_token_expire_minutes: int = 60

    database_url: str = "sqlite:///./centraldevice.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    snmp_port: int = 161
    snmp_timeout: int = 3
    snmp_retries: int = 1
    poll_interval_seconds: int = 60

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    bootstrap_admin_user: str = "admin"
    bootstrap_admin_password: str = "admin"
    bootstrap_admin_email: str = "admin@centraldevice.local"


settings = Settings()
