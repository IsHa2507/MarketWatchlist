from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://marketpulse:marketpulse@localhost:5432/marketpulse"
    JWT_SECRET: str = "hackathon-demo-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    ENVIRONMENT: str = "development"
    DEMO_MODE: bool = True

    MARKET_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
