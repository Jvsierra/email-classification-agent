from dataclasses import dataclass, field

from email_agent.models import EmailClassification, EmailMessage, SendResult


@dataclass
class FakeAssistant:
    classification: EmailClassification
    draft: str = "Thank you for your message."

    def classify(self, message: EmailMessage) -> EmailClassification:
        return self.classification

    def write(self, message: EmailMessage, classification: EmailClassification) -> str:
        return self.draft


@dataclass
class FakeSender:
    sent: list[tuple[str, str, str]] = field(default_factory=list)
    keys: set[str] = field(default_factory=set)

    def send_reply(
        self,
        message: EmailMessage,
        body: str,
        *,
        recipient_email: str,
        idempotency_key: str,
    ) -> SendResult:
        if idempotency_key not in self.keys:
            self.sent.append((message.message_id, body, idempotency_key))
            self.keys.add(idempotency_key)
        return SendResult(
            provider_message_id=f"fake-{message.message_id}",
            idempotency_key=idempotency_key,
            recipient_email=recipient_email,
        )
