from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    base_points_per_kg: float = 10.0
    points_per_cylinder: int = 1000

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
