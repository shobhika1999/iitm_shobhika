from rfp.database.repository import (
    export_run_json,
    get_leaderboard,
    get_run_context,
    save_evaluation_run,
)
from rfp.models.schemas import SupplierEvaluation
from rfp.services.run_service import run_evaluation
from rfp.tools.pdf_reader import extract_pdf_text


def _fake_evaluator(supplier, criteria):
    evaluation = SupplierEvaluation(
        supplier_name=supplier["supplier_name"],
        criteria=[
            {
                "criterion_id": c["criterion_id"],
                "score": 8,
                "justification": "Fixture justification used only for the automated integration test.",
                "evidence": "Fixture evidence marker; no procurement judgement is implied.",
            }
            for c in criteria
        ],
        risks=[],
        overall_summary="Automated test fixture; not a real supplier evaluation.",
    )
    return evaluation, [], {"model": "test-fixture", "total_tokens": 0}


def test_pdf_reader_extracts_apex_sample():
    from pathlib import Path
    pdf_path = Path(__file__).resolve().parents[1] / "sample_data/rfps/01_Apex_Systems_Proposal.pdf"
    result = extract_pdf_text(pdf_path)
    assert result["page_count"] >= 1
    assert result["status"] == "SUCCESS"
    assert len(result["extracted_text"]) > 100


def test_end_to_end_orchestration_with_fixture(isolated_db):
    from rfp.database.repository import get_active_criteria
    active = get_active_criteria()
    assert round(sum(float(c["weight"]) for c in active), 2) == 100
    run_id = save_evaluation_run([{
        "supplier_name": "Apex Systems",
        "submission_date": "2026-11-05",
        "experience_rating": 7,
        "file_name": "apex.pdf",
        "page_count": 2,
        "extracted_text": "Synthetic Apex proposal text for a test.",
        "status": "SUCCESS",
    }])
    result = run_evaluation(run_id, evaluator_fn=_fake_evaluator)
    assert result["status"] == "completed"
    assert result["evaluated_count"] == 1
    leaderboard = get_leaderboard(run_id)
    assert len(leaderboard) == 1
    assert leaderboard[0]["supplier_name"] == "Apex Systems"
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["absolute_score"] == 80.0
    # With only one supplier, every criterion equals its own benchmark, so PPI is 100%.
    assert leaderboard[0]["ppi"] == 100.0
    exported = export_run_json(run_id)
    assert exported["status"] == "completed"
    assert len(exported["suppliers"][0]["criteria"]) == 5
