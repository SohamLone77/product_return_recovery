import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Intelligent Product Returns & Recovery Engine"
    app_env: str = "development"
    debug: bool = True
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./returns.db")
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
