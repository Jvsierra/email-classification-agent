"""LangGraph workflow, with external effects injected through narrow ports."""

from functools import partial
from typing import Literal, NotRequired, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from email_agent.models import (
    EmailClassification,
    EmailMessage,
    PolicyDecision,
    ReviewDecision,
    SendResult,
)
from email_agent.policy import decide_route
from email_agent.ports import EmailClassifier, EmailSender, ResponseWriter


class EmailAgentState(TypedDict):
    message: EmailMessage
    recipient_email: NotRequired[str]
    idempotency_key: NotRequired[str]
    classification: NotRequired[EmailClassification]
    draft_response: NotRequired[str]
    policy: NotRequired[PolicyDecision]
    review_decision: NotRequired[ReviewDecision]
    send_result: NotRequired[SendResult]
    status: NotRequired[str]


def classify_node(
    state: EmailAgentState, *, classifier: EmailClassifier
) -> dict[str, object]:
    return {"classification": classifier.classify(state["message"])}


def draft_node(
    state: EmailAgentState, *, writer: ResponseWriter
) -> dict[str, object]:
    return {
        "draft_response": writer.write(state["message"], state["classification"]),
    }


def policy_node(state: EmailAgentState) -> dict[str, object]:
    return {"policy": decide_route(state["classification"], state["message"])}


def route_policy(state: EmailAgentState) -> Literal["human_review", "send_reply"]:
    return "send_reply" if state["policy"].route == "auto_send" else "human_review"


def route_preview(_: EmailAgentState) -> Literal["preview"]:
    return "preview"


def preview_node(_: EmailAgentState) -> dict[str, str]:
    return {"status": "preview_ready"}


def review_node(state: EmailAgentState) -> dict[str, object]:
    decision = ReviewDecision.model_validate(
        interrupt(
            {
                "message_id": state["message"].message_id,
                "subject": state["message"].subject,
                "sender": state["message"].sender,
                "draft_response": state["draft_response"],
                "classification": state["classification"].model_dump(mode="json"),
                "reason": state["policy"].reason,
                "action": "Approve, edit, or reject this reply.",
            }
        )
    )
    return {"review_decision": decision}


def route_review(state: EmailAgentState) -> Literal["send_reply", "rejected"]:
    return "send_reply" if state["review_decision"].approved else "rejected"


def rejected_node(_: EmailAgentState) -> dict[str, str]:
    return {"status": "rejected"}


def send_node(
    state: EmailAgentState, *, sender: EmailSender
) -> dict[str, object]:
    decision = state.get("review_decision")

    body = (
        decision.edited_response
        if decision and decision.edited_response is not None
        else state["draft_response"]
    )

    if not body.strip():
        raise ValueError("Refusing to send an empty response.")

    receipt = sender.send_reply(
        state["message"],
        body,
        recipient_email=state.get("recipient_email", state["message"].sender),
        idempotency_key=state.get("idempotency_key", state["message"].message_id),
    )

    return {"draft_response": body, "send_result": receipt, "status": "sent"}


def build_graph(
    *,
    classifier: EmailClassifier,
    writer: ResponseWriter,
    sender: EmailSender,
    checkpointer: BaseCheckpointSaver,
    preview_only: bool = False,
):
    builder = StateGraph(EmailAgentState)

    builder.add_node("classify", partial(classify_node, classifier=classifier))
    builder.add_node("draft", partial(draft_node, writer=writer))
    builder.add_node("policy", policy_node)

    builder.add_edge(START, "classify")
    builder.add_edge("classify", "draft")
    builder.add_edge("draft", "policy")

    if preview_only:
        builder.add_node("preview", preview_node)
        builder.add_conditional_edges("policy", route_preview)
        builder.add_edge("preview", END)
    else:
        builder.add_node("human_review", review_node)
        builder.add_node("rejected", rejected_node)
        builder.add_node("send_reply", partial(send_node, sender=sender))
        builder.add_conditional_edges("policy", route_policy)
        builder.add_conditional_edges("human_review", route_review)
        builder.add_edge("rejected", END)
        builder.add_edge("send_reply", END)

    return builder.compile(checkpointer=checkpointer)


def build_send_graph(
    *, sender: EmailSender, checkpointer: BaseCheckpointSaver
):
    """Compile a separate graph that sends only when explicitly invoked."""
    builder = StateGraph(EmailAgentState)
    builder.add_node("send_reply", partial(send_node, sender=sender))
    builder.add_edge(START, "send_reply")
    builder.add_edge("send_reply", END)
    return builder.compile(checkpointer=checkpointer)


