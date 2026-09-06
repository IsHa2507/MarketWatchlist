from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://marketpulse:marketpulse@localhost:5432/marketpulse"
    JWT_SECRET: str = "hackathon-demo-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    ENVIRONMENT: str = "development"
    DEMO_MODE: bool = True
    MARKET_DATA_PROVIDER: str = "demo"  # "yahoo" or "demo"
    MARKET_CACHE_TTL_SECONDS: int = 300  # 5 minutes

    MARKET_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"

    # Phase 2: news + sentiment
    NEWS_ENABLED: bool = True
    NEWS_CACHE_TTL_SECONDS: int = 3600   # 1 hour
    NEWS_MAX_ARTICLES: int = 10
    # "vader" (lexicon/rule-based) | "keyword" (zero-dependency fallback)
    # Future: "finbert" for Phase 3
    SENTIMENT_MODEL: str = "vader"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
