import json

from rfp.agents.evaluation_agent import CHAT_COMPLETIONS_URL, evaluate_supplier
from rfp.database.repository import get_active_criteria


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def test_openrouter_request_is_schema_constrained_and_normalized(isolated_db):
    criteria = get_active_criteria()
    content = {
        "supplier_name": "Apex Systems",
        "criteria": [
            {
                "criterion_id": criterion["criterion_id"],
                "score": 7,
                "justification": "A test justification based on fixture content.",
                "evidence": "Fixture evidence; this is not a real supplier assessment.",
            }
            for criterion in criteria
        ],
        "risks": [],
        "overall_summary": "Automated HTTP client test only.",
    }
    captured = {}

    def fake_post(url, *, headers, json: dict, timeout):
        captured.update({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        return FakeResponse({
            "model": "test/model",
            "choices": [{"finish_reason": "stop", "message": {"content": __import__("json").dumps(content)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        })

    evaluation, warnings, usage = evaluate_supplier(
        {
            "supplier_name": "Apex Systems",
            "extracted_text": "Proposal fixture text for the test.",
        },
        criteria,
        api_key="sk-test-placeholder",
        model_name="test/model",
        http_post=fake_post,
    )
    assert captured["url"] == CHAT_COMPLETIONS_URL
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert captured["payload"]["model"] == "test/model"
    assert len(evaluation.criteria) == len(criteria)
    assert warnings == []
    assert usage["total_tokens"] == 150
