from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rfp.database.repository import export_run_json, get_leaderboard, save_evaluation_run
from rfp.services.run_service import run_evaluation
from rfp.tools.pdf_reader import extract_pdf_text

DEFAULT_APEX_PDF = ROOT / "sample_data" / "rfps" / "01_Apex_Systems_Proposal.pdf"


def make_mock_evaluator(supplier: dict, criteria: list[dict]):
    """Deterministic offline fixture. It is NOT an AI evaluation."""
    name_to_score = {
        "technical capability": 8.5,
        "implementation plan": 7.0,
        "commercial value": 6.0,
        "security & compliance": 8.5,
        "support & experience": 7.5,
    }
    items = []
    for criterion in criteria:
        key = criterion["criterion_name"].strip().casefold()
        score = min(float(criterion["max_score"]), name_to_score.get(key, float(criterion["max_score"]) * 0.7))
        items.append({
            "criterion_id": int(criterion["criterion_id"]),
            "score": score,
            "justification": "MOCK TEST ONLY: deterministic fixture score used to verify pipeline wiring; not a substantive supplier assessment.",
            "evidence": "MOCK TEST ONLY: live model evidence extraction was not performed.",
        })
    from rfp.models.schemas import SupplierEvaluation
    return SupplierEvaluation(
        supplier_name=supplier["supplier_name"],
        criteria=items,
        risks=["MOCK TEST ONLY: replace with live AI evaluation before making procurement decisions."],
        overall_summary="MOCK TEST ONLY: this result verifies local pipeline persistence and scoring, not supplier merit.",
    ), ["Mock evaluator used; not a live OpenRouter assessment."], {"model": "offline-mock", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an isolated Apex Systems supplier evaluation.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic offline fixture instead of OpenRouter.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_APEX_PDF, help="Apex PDF path.")
    parser.add_argument("--supplier-name", default="Apex Systems")
    parser.add_argument("--submission-date", default=date.today().isoformat())
    parser.add_argument("--experience-rating", type=float, default=7.0)
    parser.add_argument("--run-id", help="Evaluate an existing saved run instead of creating a new Apex-only run.")
    args = parser.parse_args()

    if args.run_id:
        run_id = args.run_id
    else:
        if not args.pdf.exists():
            print(f"PDF not found: {args.pdf}", file=sys.stderr)
            return 2
        extracted = extract_pdf_text(args.pdf)
        if extracted["status"] != "SUCCESS":
            print(f"PDF extraction failed: {extracted['status']}", file=sys.stderr)
            return 2
        supplier = {
            "supplier_name": args.supplier_name.strip(),
            "submission_date": args.submission_date,
            "experience_rating": args.experience_rating,
            "file_name": args.pdf.name,
            "page_count": extracted["page_count"],
            "extracted_text": extracted["extracted_text"],
            "status": extracted["status"],
        }
        run_id = save_evaluation_run([supplier])

    evaluator_fn = make_mock_evaluator if args.mock else None
    mode = "OFFLINE MOCK (not a live AI evaluation)" if args.mock else "LIVE OPENROUTER"
    print(f"Mode: {mode}")
    print(f"Run ID: {run_id}")
    try:
        result = run_evaluation(run_id, evaluator_fn=evaluator_fn)
    except Exception as exc:
        print(f"Evaluation could not be completed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({k: v for k, v in result.items() if k != "leaderboard"}, indent=2))
    print("\nLEADERBOARD")
    for row in get_leaderboard(run_id):
        print(f"Rank {row['rank']}: {row['supplier_name']} | absolute={row['absolute_score']} | PPI={row['ppi']} | warnings={row['warnings_json']}")

    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{run_id.replace('/', '_')}.json"
    output_path.write_text(json.dumps(export_run_json(run_id), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull run JSON: {output_path}")
    if result["status"] != "completed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
