from langgraph.checkpoint.memory import InMemorySaver
import pytest

from email_agent.application import create_email_agent, delivery_idempotency_key
from email_agent.models import (
    EmailClassification,
    EmailIntent,
    ReviewDecision,
    Urgency,
)
from pydantic import ValidationError

from fakes import FakeAssistant, FakeSender


def test_agent_can_be_built_without_credentials():
    agent = create_email_agent(checkpointer=InMemorySaver())
    assert agent is not None


def test_safe_positive_feedback_is_sent(message, positive_classification):
    sender = FakeSender()
    assistant = FakeAssistant(positive_classification)
    agent = create_email_agent(
        checkpointer=InMemorySaver(), classifier=assistant, writer=assistant, sender=sender
    )

    result = agent.process(message, thread_id="safe-1")

    assert result.status == "sent"
    assert len(sender.sent) == 1
    assert sender.sent[0][2] == message.message_id


def test_non_allowlisted_email_pauses_and_approval_sends(message):
    classification = EmailClassification(
        intent=EmailIntent.BILLING,
        urgency=Urgency.MEDIUM,
        topic="billing",
        summary="A billing question.",
    )
    sender = FakeSender()
    assistant = FakeAssistant(classification, "We will review your billing question.")
    agent = create_email_agent(
        checkpointer=InMemorySaver(), classifier=assistant, writer=assistant, sender=sender
    )

    paused = agent.process(message, thread_id="review-1")
    assert paused.status == "awaiting_review"
    assert sender.sent == []

    sent = agent.review("review-1", ReviewDecision(approved=True, edited_response="Reviewed reply."))
    assert sent.status == "sent"
    assert sender.sent[0][1] == "Reviewed reply."


def test_rejection_never_sends(message):
    classification = EmailClassification(
        intent=EmailIntent.QUESTION,
        urgency=Urgency.LOW,
        topic="general",
        summary="A general question.",
    )
    sender = FakeSender()
    assistant = FakeAssistant(classification)
    agent = create_email_agent(
        checkpointer=InMemorySaver(), classifier=assistant, writer=assistant, sender=sender
    )

    paused = agent.process(message, thread_id="reject-1")
    assert paused.status == "awaiting_review"
    rejected = agent.review("reject-1", {"approved": False})
    assert rejected.status == "rejected"
    assert sender.sent == []


def test_approved_empty_edit_is_rejected():
    try:
        ReviewDecision(approved=True, edited_response="  ")
    except ValidationError:
        return
    raise AssertionError("An empty approved edit must fail validation.")


def test_sender_adapter_contract_deduplicates_by_message_id(message):
    sender = FakeSender()
    sender.send_reply(
        message,
        "Reply",
        recipient_email=message.sender,
        idempotency_key=message.message_id,
    )
    sender.send_reply(
        message,
        "Reply",
        recipient_email=message.sender,
        idempotency_key=message.message_id,
    )
    assert len(sender.sent) == 1


def test_preview_does_not_send_until_explicit_delivery(
    message, positive_classification
):
    sender = FakeSender()
    assistant = FakeAssistant(positive_classification)
    agent = create_email_agent(
        checkpointer=InMemorySaver(),
        classifier=assistant,
        writer=assistant,
        sender=sender,
        preview_only=True,
    )

    preview = agent.preview(message, thread_id="dashboard-preview")
    assert preview.would_auto_send is True
    assert sender.sent == []

    receipt = agent.send_preview(
        message,
        recipient_email="chosen@example.com",
        response_body=preview.draft_response,
        thread_id="dashboard-send",
    )
    assert receipt.recipient_email == "chosen@example.com"
    assert sender.sent[0][2] == delivery_idempotency_key(
        message.message_id,
        "chosen@example.com",
        preview.draft_response,
    )


def test_delivery_rejects_invalid_recipient_before_sending(
    message, positive_classification
):
    sender = FakeSender()
    assistant = FakeAssistant(positive_classification)
    agent = create_email_agent(
        checkpointer=InMemorySaver(),
        classifier=assistant,
        writer=assistant,
        sender=sender,
        preview_only=True,
    )

    with pytest.raises(ValidationError):
        agent.send_preview(
            message,
            recipient_email="not-an-email",
            response_body="A reply",
            thread_id="invalid-recipient",
        )
    assert sender.sent == []
