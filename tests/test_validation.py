import json

from rfp.database.repository import get_active_criteria
from rfp.tools.response_validator import normalize_evaluation


def test_missing_criterion_becomes_zero(isolated_db):
    criteria = get_active_criteria()
    first = criteria[0]
    payload = {
        "supplier_name": "Apex Systems",
        "criteria": [{
            "criterion_id": first["criterion_id"], "score": 8,
            "justification": "Strong architecture details.", "evidence": "Architecture section.",
        }],
        "risks": [], "overall_summary": "Partial test result.",
    }
    evaluation, warnings = normalize_evaluation(json.dumps(payload), "Apex Systems", criteria)
    assert len(evaluation.criteria) == len(criteria)
    assert evaluation.criteria[0].score == 8
    assert any(item.score == 0 for item in evaluation.criteria[1:])
    assert any("Missing result" in warning for warning in warnings)


def test_out_of_range_score_is_clipped(isolated_db):
    criteria = get_active_criteria()
    payload = {
        "supplier_name": "Apex Systems",
        "criteria": [{
            "criterion_id": c["criterion_id"], "score": 999,
            "justification": "Test justification.", "evidence": "Test evidence.",
        } for c in criteria],
        "risks": [], "overall_summary": "Test summary.",
    }
    evaluation, warnings = normalize_evaluation(json.dumps(payload), "Apex Systems", criteria)
    assert all(item.score <= 10 for item in evaluation.criteria)
    assert any("clipped" in warning for warning in warnings)


def test_unknown_duplicate_and_markdown_json_are_handled(isolated_db):
    criteria = get_active_criteria()
    first_id = criteria[0]["criterion_id"]
    payload = {
        "supplier_name": "Apex Systems",
        "criteria": [
            {"criterion_id": first_id, "score": 6, "justification": "first", "evidence": "first evidence"},
            {"criterion_id": first_id, "score": 9, "justification": "duplicate", "evidence": "duplicate evidence"},
            {"criterion_id": 9999, "score": 8, "justification": "unknown", "evidence": "unknown evidence"},
        ],
        "risks": [], "overall_summary": "Test summary.",
    }
    evaluation, warnings = normalize_evaluation("```json\n" + json.dumps(payload) + "\n```", "Apex Systems", criteria)
    assert evaluation.criteria[0].score == 6
    assert any("Duplicate" in warning for warning in warnings)
    assert any("Unknown" in warning for warning in warnings)
