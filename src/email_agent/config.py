"""Environment-backed runtime configuration."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = "claude-sonnet-4-5-20250929"
    checkpointer_backend: str = "memory"
    postgres_dsn: str | None = None
    anthropic_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        backend = os.getenv("EMAIL_AGENT_CHECKPOINTER", "memory").lower()
        if backend not in {"memory", "postgres"}:
            raise ValueError("EMAIL_AGENT_CHECKPOINTER must be 'memory' or 'postgres'.")
        dsn = os.getenv("EMAIL_AGENT_POSTGRES_DSN")
        if backend == "postgres" and not dsn:
            raise ValueError("EMAIL_AGENT_POSTGRES_DSN is required for postgres checkpointer.")
        return cls(
            model=os.getenv("EMAIL_AGENT_MODEL", "claude-sonnet-4-5-20250929"),
            checkpointer_backend=backend,
            postgres_dsn=dsn,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
