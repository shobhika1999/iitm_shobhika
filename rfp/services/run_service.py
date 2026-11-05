from __future__ import annotations

from typing import Callable

from rfp.agents.evaluation_agent import evaluate_supplier
from rfp.database import repository
from rfp.services.benchmarking_service import calculate_peer_metrics
from rfp.services.ranking_service import rank_suppliers


def run_evaluation(
    run_id: str,
    *,
    evaluator_fn: Callable | None = None,
    progress_callback: Callable | None = None,
) -> dict:
    """Evaluate every supplier in a saved run, score, benchmark, rank and persist."""
    repository.update_run_status(run_id, "evaluating")
    context = repository.get_run_context(run_id)
    criteria = context["criteria"]
    suppliers = context["suppliers"]
    if not criteria:
        repository.update_run_status(run_id, "failed", ["No criteria snapshot exists for this run."])
        raise ValueError("No criteria snapshot exists for this run.")

    evaluator = evaluator_fn or (lambda supplier, active: evaluate_supplier(supplier, active))
    successful: list[dict] = []
    failures: list[str] = []
    total = len(suppliers)

    for index, supplier in enumerate(suppliers, start=1):
        name = supplier["supplier_name"]
        if progress_callback:
            progress_callback(index, total, name, "Evaluating")
        try:
            if supplier.get("extraction_status") != "SUCCESS" or not supplier.get("extracted_text", "").strip():
                raise ValueError(f"PDF extraction is not successful: {supplier.get('extraction_status')}")
            evaluation, warnings, usage = evaluator(supplier, criteria)
            repository.update_supplier_evaluation(
                run_id, int(supplier["supplier_result_id"]), evaluation, warnings, usage
            )
            successful.append({**supplier, "evaluation": evaluation})
            if progress_callback:
                progress_callback(index, total, name, "Evaluated and validated")
        except Exception as exc:
            message = f"{name}: {type(exc).__name__}: {exc}"
            failures.append(message)
            repository.update_supplier_error(int(supplier["supplier_result_id"]), message)
            if progress_callback:
                progress_callback(index, total, name, f"Failed: {exc}")

    if successful:
        scored = calculate_peer_metrics(successful, criteria)
        ranked = rank_suppliers(scored)
        repository.save_scoring_results(run_id, ranked)

    final_status = "completed" if not failures and len(successful) == total else "failed"
    repository.update_run_status(run_id, final_status, failures)
    return {
        "run_id": run_id,
        "status": final_status,
        "supplier_count": total,
        "evaluated_count": len(successful),
        "failed_count": len(failures),
        "failures": failures,
        "leaderboard": repository.get_leaderboard(run_id),
    }
