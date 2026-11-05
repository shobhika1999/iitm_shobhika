from __future__ import annotations

import json
import math
import re
from typing import Any

from rfp.models.schemas import CriterionEvaluation, SupplierEvaluation


def _clean_json_text(raw_content: str) -> str:
    text = raw_content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    # Some gateways add a short preamble. Accept the first complete object only.
    start = text.find("{")
    if start < 0:
        raise ValueError("The AI response does not contain a JSON object.")
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"The AI response is not valid JSON: {exc}") from exc
    return payload


def normalize_evaluation(
    raw_content: str,
    expected_supplier_name: str,
    active_criteria: list[dict],
) -> tuple[SupplierEvaluation, list[str]]:
    """Parse, validate and normalize criterion results; missing scores become zero."""
    if not isinstance(raw_content, str) or not raw_content.strip():
        raise ValueError("The AI returned an empty response.")
    payload = _clean_json_text(raw_content)
    if not isinstance(payload, dict):
        raise ValueError("The AI response must be a JSON object.")
    if not active_criteria:
        raise ValueError("No active evaluation criteria were supplied.")

    warnings: list[str] = []
    returned_name = payload.get("supplier_name")
    if not isinstance(returned_name, str) or returned_name.strip() != expected_supplier_name.strip():
        warnings.append("Supplier name was missing or different; the uploaded supplier name was retained.")

    criteria_by_id = {int(c["criterion_id"]): c for c in active_criteria}
    raw_items = payload.get("criteria", [])
    if not isinstance(raw_items, list):
        raw_items = []
        warnings.append("Invalid criteria list; all active criteria will receive zero.")

    returned: dict[int, dict[str, Any]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            warnings.append("A non-object criterion result was ignored.")
            continue
        try:
            criterion_id = int(item.get("criterion_id"))
        except (TypeError, ValueError):
            warnings.append("A criterion result with an invalid criterion_id was ignored.")
            continue
        if criterion_id not in criteria_by_id:
            warnings.append(f"Unknown or inactive criterion_id {criterion_id} was ignored.")
            continue
        if criterion_id in returned:
            warnings.append(f"Duplicate result for criterion_id {criterion_id} was ignored; the first result was retained.")
            continue
        returned[criterion_id] = item

    normalized: list[CriterionEvaluation] = []
    for criterion_id, criterion in criteria_by_id.items():
        item = returned.get(criterion_id)
        if item is None:
            score = 0.0
            justification = "No valid AI result was returned for this active criterion."
            evidence = "No supporting evidence was returned."
            warnings.append(f"Missing result for {criterion['criterion_name']}; score set to zero.")
        else:
            raw_score = item.get("score", 0)
            try:
                if isinstance(raw_score, bool):
                    raise ValueError
                score = float(raw_score)
                if not math.isfinite(score):
                    raise ValueError
            except (TypeError, ValueError):
                score = 0.0
                warnings.append(f"Invalid score for {criterion['criterion_name']}; score set to zero.")

            maximum = float(criterion["max_score"])
            clipped = min(max(score, 0.0), maximum)
            if clipped != score:
                warnings.append(
                    f"Score for {criterion['criterion_name']} was outside 0-{maximum:g} and was clipped to {clipped:g}."
                )
            score = clipped

            justification = item.get("justification")
            if not isinstance(justification, str) or not justification.strip():
                justification = "The AI did not provide a usable justification."
                warnings.append(f"Missing justification for {criterion['criterion_name']}.")
            evidence = item.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                evidence = "The AI did not provide supporting evidence."
                warnings.append(f"Missing evidence for {criterion['criterion_name']}.")

        normalized.append(CriterionEvaluation(
            criterion_id=criterion_id,
            score=round(score, 2),
            justification=justification.strip(),
            evidence=evidence.strip(),
        ))

    raw_risks = payload.get("risks", [])
    if not isinstance(raw_risks, list):
        raw_risks = []
        warnings.append("Invalid risks field; an empty list was used.")
    risks = [r.strip() for r in raw_risks if isinstance(r, str) and r.strip()]
    if len(risks) != len(raw_risks):
        warnings.append("One or more invalid risk entries were ignored.")

    summary = payload.get("overall_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "No valid overall summary was returned."
        warnings.append("Missing overall summary.")

    evaluation = SupplierEvaluation(
        supplier_name=expected_supplier_name.strip(),
        criteria=normalized,
        risks=risks,
        overall_summary=summary.strip(),
    )
    return evaluation, warnings
