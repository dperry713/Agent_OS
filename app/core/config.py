from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "Agent Runtime OS"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Infrastructure
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres.default.svc.cluster.local:5432/agent_os"
    RABBITMQ_URL: str = "pyamqp://guest:guest@rabbitmq.default.svc.cluster.local//"
    VALKEY_URL: str = "redis://valkey.default.svc.cluster.local:6379/0"
    
    # Security (OpenBao / Vault)
    VAULT_ADDR: str = "http://openbao.default.svc.cluster.local:8200"
    VAULT_TOKEN: Optional[str] = None
    JWT_SECRET: str = "super-secret-key-change-in-prod"
    
    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector.monitoring:4317"
    
    # Sandbox Defaults
    SANDBOX_BACKEND: str = "gvisor" # options: process, gvisor, firecracker
    DEFAULT_SANDBOX_PROFILE: str = "strict"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
