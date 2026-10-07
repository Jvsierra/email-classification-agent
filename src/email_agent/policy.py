"""Deterministic rules that constrain when a generated reply can be sent."""

import re

from email_agent.models import (
    EmailClassification,
    EmailIntent,
    EmailMessage,
    PolicyDecision,
    Urgency,
)


_REVIEW_CUES = re.compile(
    r"\?|\b(please|help|need|want|request|refund|cancel|charge|charged|"
    r"problem|issue|broken|bug|urgent|asap|password|credential|secret|"
    r"ignore (all |any )?(previous|prior) instructions|forward|send to)\b",
    re.IGNORECASE,
)


def decide_route(
    classification: EmailClassification, message: EmailMessage
) -> PolicyDecision:
    """Auto-send only clean, low urgency positive feedback; everything else is reviewed."""
    if (
        classification.intent is EmailIntent.POSITIVE_FEEDBACK
        and classification.urgency is Urgency.LOW
        and not _REVIEW_CUES.search(f"{message.subject}\n{message.body}")
    ):
        return PolicyDecision(
            route="auto_send",
            reason="Low-urgency positive feedback is in the initial auto-send allowlist.",
        )
    return PolicyDecision(
        route="human_review",
        reason="The message is outside the low-risk allowlist or contains a review cue.",
    )
