"""Run the versioned synthetic cases against Anthropic and print a JSON report."""

import json
import os
from pathlib import Path
from time import perf_counter

from email_agent.adapters.anthropic import AnthropicEmailAssistant
from email_agent.config import Settings
from email_agent.models import EmailMessage
from email_agent.policy import decide_route


def main() -> None:
    settings = Settings.from_env()
    assistant = AnthropicEmailAssistant(
        model=settings.model, api_key=settings.anthropic_api_key
    )
    cases_path = Path(__file__).with_name("email_cases.json")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results = []

    for case in cases:
        message = EmailMessage.model_validate(case["message"])
        input_tokens_before = assistant.input_tokens
        output_tokens_before = assistant.output_tokens
        started = perf_counter()
        classification = assistant.classify(message)
        draft = assistant.write(message, classification)
        policy = decide_route(classification, message)
        elapsed = perf_counter() - started
        results.append(
            {
                "id": case["id"],
                "expected_intent": case["expected_intent"],
                "actual_intent": classification.intent.value,
                "classification_pass": classification.intent.value == case["expected_intent"],
                "expected_route": case["expected_route"],
                "actual_route": policy.route,
                "route_pass": policy.route == case["expected_route"],
                "draft": draft,
                "latency_seconds": round(elapsed, 3),
                "input_tokens": assistant.input_tokens - input_tokens_before,
                "output_tokens": assistant.output_tokens - output_tokens_before,
            }
        )

    input_rate = os.getenv("EMAIL_AGENT_INPUT_USD_PER_MILLION_TOKENS")
    output_rate = os.getenv("EMAIL_AGENT_OUTPUT_USD_PER_MILLION_TOKENS")
    if input_rate is not None and output_rate is not None:
        total_cost = (
            assistant.input_tokens * float(input_rate)
            + assistant.output_tokens * float(output_rate)
        ) / 1_000_000
    else:
        total_cost = None

    report = {
        "model": settings.model,
        "case_count": len(results),
        "classification_pass_rate": sum(row["classification_pass"] for row in results)
        / len(results),
        "route_pass_rate": sum(row["route_pass"] for row in results) / len(results),
        "input_tokens": assistant.input_tokens,
        "output_tokens": assistant.output_tokens,
        "estimated_cost_usd": total_cost,
        "pricing_configured": total_cost is not None,
        "cases": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
