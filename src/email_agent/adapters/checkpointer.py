"""Checkpointer lifecycle helpers for local and durable execution."""

from contextlib import contextmanager
from collections.abc import Iterator

from langgraph.checkpoint.base import BaseCheckpointSaver

from email_agent.config import Settings


@contextmanager
def checkpointer_context(settings: Settings) -> Iterator[BaseCheckpointSaver]:
    if settings.checkpointer_backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        yield InMemorySaver()
        return
    if settings.checkpointer_backend != "postgres" or not settings.postgres_dsn:
        raise ValueError("A postgres checkpointer requires EMAIL_AGENT_POSTGRES_DSN.")

    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(settings.postgres_dsn) as saver:
        saver.setup()
        yield saver
