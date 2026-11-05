from __future__ import annotations

from datetime import date


def _date_key(value: str) -> tuple[int, int, int]:
    try:
        parsed = date.fromisoformat(str(value)[:10])
        return parsed.year, parsed.month, parsed.day
    except (TypeError, ValueError):
        # Invalid/missing submission dates sort after valid dates.
        return 9999, 12, 31


def rank_suppliers(scored_suppliers: list[dict]) -> list[dict]:
    """Stable deterministic ranking using the brief's mandatory tie-break order."""
    ordered = sorted(
        scored_suppliers,
        key=lambda item: (
            -float(item.get("ppi") or 0.0),
            _date_key(item.get("submission_date")),
            -float(item.get("experience_rating") or 0.0),
            str(item.get("supplier_name", "")).casefold(),
        ),
    )
    for rank, supplier in enumerate(ordered, start=1):
        supplier["rank"] = rank
    return ordered
