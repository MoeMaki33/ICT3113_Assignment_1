import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    """Read a positive float from the environment; fall back to default if unusable."""
    try:
        value = float(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    # Exact Ollama tag from docs/models.md. Change it in .env / the environment to
    # switch candidate model; no source edit is needed (see docs/models.md).
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")
    # Seconds to wait for one blocking classification request.
    ollama_timeout: float = _float_env("OLLAMA_TIMEOUT_SECONDS", 120.0)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/tickets.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
