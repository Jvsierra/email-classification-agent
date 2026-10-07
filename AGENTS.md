# Repository Guidelines

## Project Structure

The application lives in `src/email_agent/`: validated contracts and configuration are separate from the LangGraph workflow, deterministic policy, and external adapters. `tests/` contains offline checks with fakes, while `evals/email_cases.json` holds synthetic behavior and safety cases. `Email Agent.ipynb` and `agent-flow.jpeg` preserve the original prototype and diagram.

## Setup and Commands

- `python -m venv .venv` creates an isolated environment; activate it before installing dependencies.
- `python -m pip install -e ".[dev]"` installs the package and pytest tools.
- `streamlit run dashboard.py` launches the dashboard; delivery requires SMTP configuration and the explicit **Send reply** action.
- Copy `.env.sample` to `.env` for local settings. Model-backed runs need `ANTHROPIC_API_KEY`; tests and graph construction do not.
- `pytest` runs the offline test suite without calling external services.

## Style and Design

Use Python 3.11+, four-space indentation, `snake_case` for functions and variables, and `PascalCase` for types. Keep model and provider access behind protocols in `ports.py`; inject fakes in tests. SMTP is the default sender. Dashboard delivery must require an explicit user action and must use the address entered in the UI. Do not log message bodies, prompts, credentials, or other customer content.

## Testing and Evaluation

Add regression cases for policy decisions, approval/resume, rejection, and send idempotency. Use synthetic inputs in committed evaluations. When changing model behavior, compare classification and routing against `evals/email_cases.json` and review draft quality before widening the automatic-send allowlist. Never require a live model or email account for unit tests.

## Configuration and Persistence

Configuration uses the `ANTHROPIC_*`, `EMAIL_AGENT_*`, and `SMTP_*` settings documented in `.env.sample`. Optional per-million-token rates let the evaluation runner estimate cost. SMTP is secured with STARTTLS by default; `SMTP_USE_SSL=true` enables implicit TLS. Memory persistence is for local use; PostgreSQL is required for durable review and resume. Checkpoints can contain email content, so document and enforce an operational retention schedule in any deployed environment.

## Commits and Pull Requests

Use short, imperative commit subjects (for example, `Add review resume handling`). Pull requests should describe behavior and policy changes, list configuration or dependency updates, and report relevant tests and synthetic evaluation results. Link related issues when available.
