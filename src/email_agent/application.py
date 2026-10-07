"""Application facade for starting and resuming email workflows."""

from contextlib import contextmanager
from collections.abc import Iterator
from hashlib import sha256

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from email_agent.adapters.anthropic import AnthropicEmailAssistant
from email_agent.adapters.checkpointer import checkpointer_context
from email_agent.adapters.smtp import SMTPEmailSender
from email_agent.config import Settings
from email_agent.graph import build_graph, build_send_graph
from email_agent.models import (
    EmailDeliveryRequest,
    EmailMessage,
    EmailPreview,
    EmailResult,
    ReviewDecision,
    SendResult,
)
from email_agent.ports import EmailClassifier, EmailSender, ResponseWriter


class EmailAgent:
    def __init__(
        self, graph, *, preview_only: bool = False, usage_source=None, send_graph=None
    ) -> None:
        self._graph = graph
        self._preview_only = preview_only
        self._usage_source = usage_source
        self._send_graph = send_graph

    def process(self, message: EmailMessage | dict, *, thread_id: str) -> EmailResult:
        if self._preview_only:
            raise RuntimeError("Use preview() for an agent built with preview_only=True.")
        validated = EmailMessage.model_validate(message)
        state = self._graph.invoke(
            {"message": validated}, self._config(thread_id)
        )
        return self._result(validated, state)

    def review(self, thread_id: str, decision: ReviewDecision | dict) -> EmailResult:
        validated = ReviewDecision.model_validate(decision)
        state = self._graph.invoke(
            Command(resume=validated.model_dump(mode="json")), self._config(thread_id)
        )
        message = EmailMessage.model_validate(state["message"])
        return self._result(message, state)

    def preview(self, message: EmailMessage | dict, *, thread_id: str) -> EmailPreview:
        if not self._preview_only:
            raise RuntimeError("Preview requires an agent built with preview_only=True.")

        validated = EmailMessage.model_validate(message)
        input_before = getattr(self._usage_source, "input_tokens", 0)
        output_before = getattr(self._usage_source, "output_tokens", 0)
        state = self._graph.invoke(
            {"message": validated}, self._config(thread_id)
        )

        return EmailPreview(
            message_id=validated.message_id,
            classification=state["classification"],
            draft_response=state["draft_response"],
            policy=state["policy"],
            would_auto_send=state["policy"].route == "auto_send",
            input_tokens=getattr(self._usage_source, "input_tokens", 0) - input_before,
            output_tokens=getattr(self._usage_source, "output_tokens", 0) - output_before,
        )

    def send_preview(
        self,
        message: EmailMessage | dict,
        *,
        recipient_email: str,
        response_body: str,
        thread_id: str,
    ) -> SendResult:
        """Send a user-approved preview using the dedicated delivery graph."""
        if not self._preview_only or self._send_graph is None:
            raise RuntimeError("Sending a preview requires a preview-mode agent.")

        validated_message = EmailMessage.model_validate(message)
        request = EmailDeliveryRequest(
            recipient_email=recipient_email,
            response_body=response_body,
        )
        idempotency_key = delivery_idempotency_key(
            validated_message.message_id,
            str(request.recipient_email),
            request.response_body,
        )
        state = self._send_graph.invoke(
            {
                "message": validated_message,
                "recipient_email": str(request.recipient_email),
                "draft_response": request.response_body,
                "idempotency_key": idempotency_key,
            },
            self._config(thread_id),
        )
        return SendResult.model_validate(state["send_result"])

    @staticmethod
    def _config(thread_id: str) -> dict:
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty.")
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _result(message: EmailMessage, state: dict) -> EmailResult:
        if "__interrupt__" in state:
            status = "awaiting_review"
        else:
            status = state["status"]
        return EmailResult(
            message_id=message.message_id,
            status=status,
            classification=state["classification"],
            draft_response=state["draft_response"],
            policy=state["policy"],
            send_result=state.get("send_result"),
        )


def create_email_agent(
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    classifier: EmailClassifier | None = None,
    writer: ResponseWriter | None = None,
    sender: EmailSender | None = None,
    settings: Settings | None = None,
    preview_only: bool = False,
) -> EmailAgent:
    """Build the agent without contacting a model or email provider."""

    runtime = settings or Settings.from_env()

    if checkpointer is None and runtime.checkpointer_backend == "postgres":
        raise ValueError(
            "Use email_agent_context() or pass a live PostgreSQL checkpointer when "
            "EMAIL_AGENT_CHECKPOINTER=postgres."
        )

    usage_source = None
    if classifier is None or writer is None:
        assistant = AnthropicEmailAssistant(
            model=runtime.model, api_key=runtime.anthropic_api_key
        )
        usage_source = assistant

        classifier = classifier if classifier is not None else assistant

        writer = writer if writer is not None else assistant

    delivery_sender = sender if sender is not None else SMTPEmailSender.from_env()

    graph = build_graph(
        classifier=classifier,
        writer=writer,
        sender=delivery_sender,
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        preview_only=preview_only,
    )
    delivery_graph = (
        build_send_graph(
            sender=delivery_sender,
            checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        )
        if preview_only
        else None
    )

    return EmailAgent(
        graph,
        preview_only=preview_only,
        usage_source=usage_source,
        send_graph=delivery_graph,
    )


def delivery_idempotency_key(
    message_id: str, recipient_email: str, response_body: str
) -> str:
    """Stable key for repeated clicks on the same message, recipient, and reply."""
    value = f"{message_id}\0{recipient_email.casefold()}\0{response_body}"
    return sha256(value.encode("utf-8")).hexdigest()


@contextmanager
def email_agent_context(
    *,
    settings: Settings | None = None,
    classifier: EmailClassifier | None = None,
    writer: ResponseWriter | None = None,
    sender: EmailSender | None = None,
) -> Iterator[EmailAgent]:
    """Create an agent whose checkpointer resources live for the context duration."""
    runtime = settings or Settings.from_env()
    
    with checkpointer_context(runtime) as checkpointer:
        yield create_email_agent(
            settings=runtime,
            checkpointer=checkpointer,
            classifier=classifier,
            writer=writer,
            sender=sender,
        )


