import pytest

from email_agent.models import (
    EmailClassification,
    EmailIntent,
    EmailMessage,
    Urgency,
)


@pytest.fixture
def positive_classification() -> EmailClassification:
    return EmailClassification(
        intent=EmailIntent.POSITIVE_FEEDBACK,
        urgency=Urgency.LOW,
        topic="service",
        summary="The customer shared positive feedback.",
    )


@pytest.fixture
def message() -> EmailMessage:
    return EmailMessage(
        message_id="msg-001",
        subject="Thanks",
        body="I loved the service. Thank you very much!",
        sender="customer@example.com",
    )
