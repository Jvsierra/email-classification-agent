"""Provider-neutral email classification and response workflow."""

from email_agent.application import EmailAgent, create_email_agent, email_agent_context
from email_agent.models import (
    EmailClassification,
    EmailDeliveryRequest,
    EmailMessage,
    EmailPreview,
    EmailResult,
    ReviewDecision,
    Urgency,
)

__all__ = [
    "EmailAgent",
    "EmailClassification",
    "EmailDeliveryRequest",
    "EmailMessage",
    "EmailPreview",
    "EmailResult",
    "ReviewDecision",
    "Urgency",
    "create_email_agent",
    "email_agent_context",
]
