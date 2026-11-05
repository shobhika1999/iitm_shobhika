"""Public orchestration entry point for the RFP evaluation workflow."""

from rfp.services.run_service import run_evaluation


def evaluate_run(run_id: str, progress_callback=None) -> dict:
    """Run AI evaluation, validation, deterministic scoring and ranking."""
    return run_evaluation(run_id, progress_callback=progress_callback)
