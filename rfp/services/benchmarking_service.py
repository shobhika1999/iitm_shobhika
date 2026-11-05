from __future__ import annotations

from rfp.services.scoring_service import calculate_absolute_score


def calculate_peer_metrics(suppliers: list[dict], criteria: list[dict]) -> list[dict]:
    """Calculate criterion benchmarks, gaps, relative %, absolute score and PPI."""
    if not suppliers:
        return []
    benchmarks: dict[int, float] = {}
    score_maps: dict[int, dict[int, float]] = {}

    for supplier in suppliers:
        result = supplier.get("evaluation") or {}
        result = result.model_dump() if hasattr(result, "model_dump") else result
        score_map = {int(c["criterion_id"]): float(c["score"]) for c in result.get("criteria", [])}
        score_maps[int(supplier["supplier_result_id"])] = score_map

    for criterion in criteria:
        cid = int(criterion["criterion_id"])
        values = [scores.get(cid, 0.0) for scores in score_maps.values()]
        benchmarks[cid] = max(values, default=0.0)

    scored: list[dict] = []
    for supplier in suppliers:
        sid = int(supplier["supplier_result_id"])
        result = supplier.get("evaluation") or {}
        result = result.model_dump() if hasattr(result, "model_dump") else result
        criterion_scores = result.get("criteria", [])
        metrics: list[dict] = []
        ppi = 0.0
        for criterion in criteria:
            cid = int(criterion["criterion_id"])
            score = score_maps[sid].get(cid, 0.0)
            benchmark = benchmarks[cid]
            # When the peer benchmark is zero, all suppliers scored zero; treat as 100% parity.
            relative = 100.0 if benchmark == 0 else (score / benchmark) * 100.0
            contribution = relative * (float(criterion["weight"]) / 100.0)
            ppi += contribution
            metrics.append({
                "criterion_id": cid,
                "criterion_name": criterion["criterion_name"],
                "score": round(score, 4),
                "max_score": float(criterion["max_score"]),
                "weight": float(criterion["weight"]),
                "benchmark_score": round(benchmark, 4),
                "gap": round(score - benchmark, 4),
                "relative_performance": round(relative, 4),
                "weighted_ppi_contribution": round(contribution, 4),
            })
        scored.append({
            **supplier,
            "absolute_score": calculate_absolute_score(criterion_scores, criteria),
            "ppi": round(ppi, 4),
            "criterion_metrics": metrics,
        })
    return scored
