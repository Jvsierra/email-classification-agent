import json
from pathlib import Path

import pytest

from email_agent.models import EmailClassification, EmailMessage
from email_agent.policy import decide_route


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).parents[1] / "evals" / "email_cases.json").read_text(encoding="utf-8")),
    ids=lambda case: case["id"],
)
def test_synthetic_evaluation_routes(case):
    message = EmailMessage.model_validate(case["message"])
    classification = EmailClassification(
        intent=case["expected_intent"],
        urgency="low",
        topic="evaluation",
        summary="Expected synthetic evaluation classification.",
    )

    assert decide_route(classification, message).route == case["expected_route"]
