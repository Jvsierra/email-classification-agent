"""Boundaries to model, knowledge, and email provider integrations."""

from typing import Protocol

from email_agent.models import EmailClassification, EmailMessage, SendResult


class EmailClassifier(Protocol):
    def classify(self, message: EmailMessage) -> EmailClassification: ...


class ResponseWriter(Protocol):
    def write(self, message: EmailMessage, classification: EmailClassification) -> str: ...


class EmailSender(Protocol):
    def send_reply(
        self,
        message: EmailMessage,
        body: str,
        *,
        recipient_email: str,
        idempotency_key: str,
    ) -> SendResult: ...


class KnowledgeBase(Protocol):
    def search(self, query: str) -> list[str]: ...
