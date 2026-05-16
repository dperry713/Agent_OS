from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Runtime OS"
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_os.db"
    REDIS_URL: str = "redis://localhost:6379"
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
