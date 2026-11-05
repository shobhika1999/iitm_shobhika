from __future__ import annotations


def calculate_absolute_score(criterion_scores: list[dict], criteria: list[dict]) -> float:
    """Return a 0-100 weighted score: sum((score / max_score) * weight)."""
    if not criteria:
        raise ValueError("Cannot score a supplier without criteria.")
    total_weight = sum(float(c["weight"]) for c in criteria)
    if round(total_weight, 2) != 100:
        raise ValueError(f"Active criteria weights must total 100%; found {total_weight:g}%.")
    scores_by_id = {int(item["criterion_id"]): float(item["score"]) for item in criterion_scores}
    total = 0.0
    for criterion in criteria:
        cid = int(criterion["criterion_id"])
        maximum = float(criterion["max_score"])
        if maximum <= 0:
            raise ValueError(f"Maximum score for criterion {cid} must be positive.")
        score = scores_by_id.get(cid, 0.0)
        score = min(max(score, 0.0), maximum)
        total += (score / maximum) * float(criterion["weight"])
    return round(total, 4)
