"""Streamlit demo dashboard for previewing and explicitly sending replies."""

import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import streamlit as st

from email_agent.application import create_email_agent, delivery_idempotency_key
from email_agent.config import Settings


CASES_PATH = Path(__file__).parent / "evals" / "email_cases.json"


@st.cache_data
def load_examples() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


st.set_page_config(page_title="Email Agent Demo", page_icon="✉️")
st.title("Email Agent Demo")
st.caption("Email classification, reply drafting, and sending policy with explicit delivery.")
st.info("The agent never sends automatically. A reply is sent only when you click 'Send reply'.")

examples = load_examples()
selected = st.selectbox(
    "Select a test email",
    examples,
    format_func=lambda case: f"{case['id']} — {case['message']['subject']}",
)

with st.expander("Selected email", expanded=True):
    st.write(f"**From:** {selected['message']['sender']}")
    st.write(f"**Subject:** {selected['message']['subject']}")
    st.write(selected["message"]["body"])

if st.button("Run agent", type="primary"):
    st.session_state.pop("dashboard_result", None)
    st.session_state.pop("dashboard_case_id", None)
    try:
        settings = replace(
            Settings.from_env(),
            checkpointer_backend="memory",
            postgres_dsn=None,
        )
        agent = create_email_agent(settings=settings, preview_only=True)
        result = agent.preview(
            selected["message"],
            thread_id=f"dashboard-{uuid4()}",
        )
        st.session_state["dashboard_result"] = result
        st.session_state["dashboard_case_id"] = selected["id"]
        st.session_state.pop("manual_reply", None)
    except Exception as exc:
        st.error(f"Could not run the agent: {exc}")

result = st.session_state.get("dashboard_result")
if result is not None and st.session_state.get("dashboard_case_id") == selected["id"]:
    st.divider()
    st.header("Agent steps")

    st.subheader("1. Classification")
    st.write(f"**Intent:** {result.classification.intent.value}")
    st.write(f"**Urgency:** {result.classification.urgency.value}")
    st.write(f"**Topic:** {result.classification.topic}")
    st.write(f"**Summary:** {result.classification.summary}")

    st.subheader("2. Draft")
    st.text_area("Suggested reply", result.draft_response, height=140, disabled=True)

    st.subheader("3. Sending policy")
    if result.would_auto_send:
        st.success(f"The policy would allow automatic sending. {result.policy.reason}")
    else:
        st.warning(f"The policy requires human review. {result.policy.reason}")

    st.subheader("4. Final reply (preview)")
    if result.would_auto_send:
        final_response = result.draft_response
        st.caption("This is the reply that would be sent automatically; it has not been sent.")
    else:
        final_response = st.text_area(
            "Write the reply you would send",
            key="manual_reply",
            height=140,
            placeholder="Type your reply here...",
        )
    if final_response.strip():
        st.write(final_response)
    elif not result.would_auto_send:
        st.caption("Your final reply will appear here once you write one.")

    st.subheader("5. Send reply")
    recipient_email = st.text_input(
        "Recipient email address",
        placeholder="name@example.com",
        key="recipient_email",
    )
    send_key = delivery_idempotency_key(
        result.message_id,
        recipient_email.strip(),
        final_response,
    ) if recipient_email.strip() and final_response.strip() else ""
    sent_delivery_keys = st.session_state.get("sent_delivery_keys", set())
    already_sent = bool(send_key) and send_key in sent_delivery_keys
    if already_sent:
        st.success(f"Reply sent to {recipient_email}.")

    if st.button(
        "Send reply",
        disabled=not recipient_email.strip() or not final_response.strip() or already_sent,
    ):
        try:
            settings = replace(
                Settings.from_env(),
                checkpointer_backend="memory",
                postgres_dsn=None,
            )
            agent = create_email_agent(
                settings=settings,
                preview_only=True,
            )
            receipt = agent.send_preview(
                selected["message"],
                recipient_email=recipient_email,
                response_body=final_response,
                thread_id=f"dashboard-send-{uuid4()}",
            )
            sent_delivery_keys = set(sent_delivery_keys)
            sent_delivery_keys.add(send_key)
            st.session_state["sent_delivery_keys"] = sent_delivery_keys
            st.success(f"Reply sent to {receipt.recipient_email}.")
        except Exception as exc:
            st.error(f"Could not send the reply: {exc}")

    st.subheader("Token usage for this run")
    input_col, output_col = st.columns(2)
    input_col.metric("Input tokens", result.input_tokens)
    output_col.metric("Output tokens", result.output_tokens)
