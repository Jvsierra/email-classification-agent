# Repository Guidelines

## Project Structure

This repository is a small notebook prototype for classifying and responding to email with a LangGraph workflow. The main implementation and examples are in [`Email Agent.ipynb`](Email%20Agent.ipynb). Its flow diagram is [`agent-flow.jpeg`](agent-flow.jpeg), and Python dependencies are listed in `requirements.txt`. There is currently no separate source package or test directory; keep prototype changes in the notebook unless the project is deliberately being split into modules.

## Setup and Development

- `python -m venv .venv` creates an isolated Python environment.
- Activate the environment, then run `pip install -r requirements.txt` to install the listed dependencies.
- Copy `.env.sample` to `.env` and set `ANTHROPIC_API_KEY` before running model-backed cells. Never commit `.env` or real credentials.
- Launch `jupyter lab` (or `jupyter notebook`) and open `Email Agent.ipynb` to inspect and run the workflow.

There is no build command or configured test runner at present. Run notebook cells from top to bottom to exercise the prototype; model calls require a valid API key and may incur provider usage.

## Style and Notebook Practices

Use standard Python conventions: four spaces for indentation, `snake_case` for functions and variables, and `PascalCase` for types. Keep graph node names descriptive and consistent with the workflow (`classify_intent`, `write_response`). Organize notebook content with Markdown headings followed by focused code cells. Preserve useful sample inputs, but do not store customer email data or credentials in committed outputs.

## Testing and Review

No automated tests or coverage requirements are configured. When changing workflow behavior, execute the affected notebook path and include representative cases for different intents or urgency levels. Clear stale outputs before committing if they contain sensitive or misleading data.

## Commits and Pull Requests

The existing history is too small to establish a strict commit convention. Use short, imperative commit subjects (for example, `Add billing email routing`). A pull request should explain the behavior changed, note any required configuration or dependency updates, and include relevant notebook results or screenshots when they clarify the change. Link a related issue when one exists.
