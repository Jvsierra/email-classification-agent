# Email Classification Agent

A provider-neutral LangGraph workflow that classifies inbound email, drafts a response, applies a deterministic send policy, and pauses for human review when needed. The package is the implementation; `Email Agent.ipynb` remains the original visual prototype.

## Project layout

- `src/email_agent/` — validated models, graph, application facade, policy, and integration ports/adapters.
- `tests/` — offline policy and graph tests using simulated model and mail adapters.
- `evals/email_cases.json` — synthetic, versioned classification and safety scenarios.
- `agent-flow.jpeg` — original workflow diagram.

## Local setup

Requires Python 3.11 or newer. Create and activate a virtual environment, then install the package and development tools:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Copy `.env.sample` to `.env`. `ANTHROPIC_API_KEY` and `EMAIL_AGENT_MODEL` configure model-backed runs. The package loads `.env` automatically. Constructing the graph and running the simulated tests do not require credentials.

## Dashboard

Run `streamlit run dashboard.py` after setup and configuring `ANTHROPIC_API_KEY` plus SMTP settings in `.env`. Choose a synthetic email, click **Run agent**, review the draft, enter the recipient address, then click **Send reply**. The preview graph cannot send. Delivery is a separate graph invocation, triggered only by the button, through SMTP using STARTTLS by default (or implicit SSL when configured).

## Use and review

`SMTPEmailSender` is the default sender for `create_email_agent()` and the dashboard. Configure `SMTP_HOST`, `SMTP_PORT`, and `SMTP_FROM_EMAIL`, plus `SMTP_USERNAME` and `SMTP_PASSWORD` when authentication is needed. Constructing the agent does not connect or send; SMTP configuration is validated when a delivery is attempted. The dashboard requires an explicit **Send reply** click, while the regular `process()` graph can send automatically when the policy allows it. The SMTP adapter uses a stable Message-ID and protects against duplicate calls within its process; SMTP servers do not guarantee idempotency across process crashes. `create_email_agent()` uses an in-memory checkpointer for local work; use `with email_agent_context() as agent:` with the PostgreSQL settings for durable approval and resume. Keep the same `thread_id` when resuming a pending review.

Only low-urgency positive feedback with no conservative review cues is eligible for automatic sending. Every other message pauses for approval, editing, or rejection. This is a narrow initial policy, not a substitute for human review of a new use case. The `KnowledgeBase` port is an integration seam only; no factual retrieval or claims are enabled yet.

## Configuration, privacy, and retention

Supported settings include `ANTHROPIC_API_KEY`, `EMAIL_AGENT_MODEL`, `EMAIL_AGENT_CHECKPOINTER` (`memory` or `postgres`), `EMAIL_AGENT_POSTGRES_DSN`, and the SMTP variables in `.env.sample`. Use a dedicated database role and apply an operational retention schedule to checkpoints; checkpoints can contain email text and draft replies. Do not log message bodies, credentials, or model prompts. The repository does not choose an API server or deployment platform.

## Tests and evaluation

Run `pytest`. Tests use fake ports and do not make network calls. The synthetic cases in `evals/email_cases.json` cover positive feedback, mixed requests, prompt injection, and sensitive content. With a configured API key, run `python evals/run_model_evaluation.py` to report classification and routing pass rates, draft text, latency, and token usage. Set `EMAIL_AGENT_INPUT_USD_PER_MILLION_TOKENS` and `EMAIL_AGENT_OUTPUT_USD_PER_MILLION_TOKENS` to calculate an estimated cost using current provider rates; cost remains unset otherwise. Review draft quality before widening the auto-send allowlist.
