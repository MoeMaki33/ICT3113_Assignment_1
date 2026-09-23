import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/tickets.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
