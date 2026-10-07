"""Validated application contracts for the email agent."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class EmailIntent(StrEnum):
    QUESTION = "question"
    BUG = "bug"
    BILLING = "billing"
    FEATURE = "feature"
    COMPLEX = "complex"
    POSITIVE_FEEDBACK = "positive_feedback"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailMessage(BaseModel):
    """A single inbound email. `message_id` is also used for send idempotency."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message_id: str = Field(min_length=1, max_length=255)
    subject: str = Field(default="", max_length=998)
    body: str = Field(min_length=1, max_length=100_000)
    sender: str = Field(min_length=3, max_length=320)


class EmailClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: EmailIntent
    urgency: Urgency
    topic: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str = Field(pattern="^(auto_send|human_review)$")
    reason: str = Field(min_length=1, max_length=500)


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    edited_response: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def require_nonempty_approved_reply(self) -> "ReviewDecision":
        if self.approved and self.edited_response is not None and not self.edited_response.strip():
            raise ValueError("An approved edited response cannot be empty.")
        return self


class SendResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_message_id: str
    idempotency_key: str
    recipient_email: EmailStr | None = None


class EmailDeliveryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    recipient_email: EmailStr
    response_body: str = Field(min_length=1, max_length=20_000)

    @model_validator(mode="after")
    def require_nonempty_response(self) -> "EmailDeliveryRequest":
        if not self.response_body.strip():
            raise ValueError("The reply cannot be empty.")
        return self


class EmailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    status: str = Field(pattern="^(awaiting_review|rejected|sent)$")
    classification: EmailClassification
    draft_response: str
    policy: PolicyDecision
    send_result: SendResult | None = None


class EmailPreview(BaseModel):
    """Result of a graph run that cannot reach the email sending node."""

    model_config = ConfigDict(extra="forbid")

    message_id: str
    classification: EmailClassification
    draft_response: str
    policy: PolicyDecision
    would_auto_send: bool
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
