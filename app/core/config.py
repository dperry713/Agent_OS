from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Runtime OS"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres.default.svc.cluster.local:5432/agent_os"
    RABBITMQ_URL: str = "pyamqp://guest:guest@rabbitmq.default.svc.cluster.local//"
    VALKEY_URL: str = "redis://valkey.default.svc.cluster.local:6379/0"
    VAULT_ADDR: str = "http://openbao.default.svc.cluster.local:8200"
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()

