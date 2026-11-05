from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rfp.database.connection import DB_PATH, get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_CRITERIA = [
    ("Technical Capability", "Technical architecture, functionality, scalability and integration capability.", 30.0, 10.0),
    ("Implementation Plan", "Project timeline, delivery methodology, milestones and implementation team.", 20.0, 10.0),
    ("Commercial Value", "Pricing competitiveness, cost transparency and overall value for money.", 20.0, 10.0),
    ("Security & Compliance", "Information security, data protection, access control and regulatory compliance.", 20.0, 10.0),
    ("Support & Experience", "Customer support, service commitments, references and relevant project experience.", 10.0, 10.0),
]
TIE_BREAK_RULE = "PPI descending, submission date ascending, experience rating descending, supplier name ascending"


def initialize_database(seed: bool = True) -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Safe migration for databases created by the earlier project version.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(supplier_results)")}
        if "result_json" not in columns:
            conn.execute("ALTER TABLE supplier_results ADD COLUMN result_json TEXT")
        if "usage_json" not in columns:
            conn.execute("ALTER TABLE supplier_results ADD COLUMN usage_json TEXT NOT NULL DEFAULT '{}'" )
        if seed:
            count = conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO evaluation_criteria (criterion_name, description, weight, max_score) VALUES (?, ?, ?, ?)",
                    DEFAULT_CRITERIA,
                )


def get_all_criteria() -> list[dict]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM evaluation_criteria ORDER BY criterion_id").fetchall()
        return [dict(row) for row in rows]


def get_active_criteria() -> list[dict]:
    return [row for row in get_all_criteria() if row["is_active"] == 1]


def save_criteria(criteria: list[dict]) -> None:
    if not criteria:
        raise ValueError("At least one criterion must be active.")
    active_weight = sum(float(c["weight"]) for c in criteria if c.get("is_active", 1))
    active_count = sum(1 for c in criteria if c.get("is_active", 1))
    if active_count == 0 or round(active_weight, 2) != 100:
        raise ValueError(f"Active criteria weights must total 100%; current total is {active_weight:g}%.")
    with get_connection() as conn:
        for item in criteria:
            conn.execute(
                "UPDATE evaluation_criteria SET criterion_name=?, description=?, weight=?, max_score=?, is_active=?, updated_at=CURRENT_TIMESTAMP WHERE criterion_id=?",
                (item["criterion_name"].strip(), item["description"].strip(), float(item["weight"]),
                 float(item["max_score"]), int(bool(item["is_active"])), int(item["criterion_id"])),
            )


def save_evaluation_run(suppliers: list[dict]) -> str:
    if not suppliers:
        raise ValueError("No supplier documents were provided.")
    names = [str(s.get("supplier_name", "")).strip().casefold() for s in suppliers]
    if any(not name for name in names):
        raise ValueError("Every supplier must have a name.")
    if len(set(names)) != len(names):
        raise ValueError("Supplier names must be unique within a batch.")
    initialize_database()
    with get_connection() as conn:
        criteria = conn.execute(
            "SELECT criterion_id, criterion_name, description, weight, max_score FROM evaluation_criteria WHERE is_active=1 ORDER BY criterion_id"
        ).fetchall()
        if not criteria:
            raise ValueError("No active evaluation criteria found.")
        total_weight = sum(float(row["weight"]) for row in criteria)
        if round(total_weight, 2) != 100:
            raise ValueError(f"Active criteria weights must total 100%; current total is {total_weight:g}%.")
        run_id = "RFP-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()
        warnings = [f"{s['supplier_name']}: {s.get('status')}" for s in suppliers if s.get("status") != "SUCCESS"]
        conn.execute(
            "INSERT INTO rfp_runs (run_id,status,criteria_total_weight,supplier_count,warnings_json,tie_break_rule) VALUES (?,?,?,?,?,?)",
            (run_id, "created", total_weight, len(suppliers), json.dumps(warnings), TIE_BREAK_RULE),
        )
        conn.executemany(
            "INSERT INTO run_criteria_snapshot (run_id,criterion_id,criterion_name,description,weight,max_score) VALUES (?,?,?,?,?,?)",
            [(run_id, int(c["criterion_id"]), c["criterion_name"], c["description"], float(c["weight"]), float(c["max_score"])) for c in criteria],
        )
        for supplier in suppliers:
            name = str(supplier["supplier_name"]).strip()
            cursor = conn.execute(
                """INSERT INTO supplier_results
                (run_id,supplier_name,submission_date,experience_rating,file_name,page_count,warnings_json)
                VALUES (?,?,?,?,?,?,?)""",
                (run_id, name, str(supplier["submission_date"]), float(supplier["experience_rating"]),
                 str(supplier["file_name"]), int(supplier.get("page_count", 0)),
                 json.dumps([] if supplier.get("status") == "SUCCESS" else [supplier.get("status", "Extraction failed")])),
            )
            conn.execute(
                "INSERT INTO supplier_documents (supplier_result_id,file_name,page_count,extracted_text,extraction_status) VALUES (?,?,?,?,?)",
                (cursor.lastrowid, str(supplier["file_name"]), int(supplier.get("page_count", 0)),
                 supplier.get("extracted_text", ""), supplier.get("status", "UNKNOWN")),
            )
        return run_id


def get_run_context(run_id: str) -> dict:
    initialize_database()
    with get_connection() as conn:
        run = conn.execute("SELECT * FROM rfp_runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ValueError(f"RFP run not found: {run_id}")
        criteria = conn.execute("SELECT * FROM run_criteria_snapshot WHERE run_id=? ORDER BY criterion_id", (run_id,)).fetchall()
        suppliers = conn.execute(
            """SELECT sr.*, sd.extracted_text, sd.extraction_status
               FROM supplier_results sr JOIN supplier_documents sd USING(supplier_result_id)
               WHERE sr.run_id=? ORDER BY sr.supplier_result_id""", (run_id,),
        ).fetchall()
        return {"run": dict(run), "criteria": [dict(r) for r in criteria], "suppliers": [dict(r) for r in suppliers]}


def update_supplier_evaluation(run_id: str, supplier_result_id: int, evaluation: Any, warnings: list[str], usage: dict) -> None:
    evaluation_dict = evaluation.model_dump() if hasattr(evaluation, "model_dump") else evaluation
    with get_connection() as conn:
        criteria = conn.execute("SELECT * FROM run_criteria_snapshot WHERE run_id=? ORDER BY criterion_id", (run_id,)).fetchall()
        criterion_by_id = {int(c["criterion_id"]): dict(c) for c in criteria}
        conn.execute(
            "UPDATE supplier_results SET overall_summary=?, risks_json=?, warnings_json=?, result_json=?, usage_json=? WHERE supplier_result_id=? AND run_id=?",
            (evaluation_dict["overall_summary"], json.dumps(evaluation_dict.get("risks", [])), json.dumps(warnings),
             json.dumps(evaluation_dict, ensure_ascii=False), json.dumps(usage or {}), supplier_result_id, run_id),
        )
        conn.execute("DELETE FROM criterion_results WHERE supplier_result_id=?", (supplier_result_id,))
        for item in evaluation_dict["criteria"]:
            cid = int(item["criterion_id"])
            criterion = criterion_by_id[cid]
            conn.execute(
                """INSERT INTO criterion_results
                (supplier_result_id,run_id,criterion_id,criterion_name,score,max_score,justification,evidence)
                VALUES (?,?,?,?,?,?,?,?)""",
                (supplier_result_id, run_id, cid, criterion["criterion_name"], float(item["score"]),
                 float(criterion["max_score"]), item["justification"], item["evidence"]),
            )


def update_supplier_error(supplier_result_id: int, message: str) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT warnings_json FROM supplier_results WHERE supplier_result_id=?", (supplier_result_id,)).fetchone()
        warnings = json.loads(row["warnings_json"] or "[]") if row else []
        warnings.append(message)
        conn.execute("UPDATE supplier_results SET warnings_json=? WHERE supplier_result_id=?", (json.dumps(warnings), supplier_result_id))


def update_run_status(run_id: str, status: str, warnings: list[str] | None = None) -> None:
    if status not in {"created", "evaluating", "completed", "failed"}:
        raise ValueError(f"Unsupported run status: {status}")
    with get_connection() as conn:
        current = conn.execute("SELECT warnings_json FROM rfp_runs WHERE run_id=?", (run_id,)).fetchone()
        if not current:
            raise ValueError(f"RFP run not found: {run_id}")
        existing = json.loads(current["warnings_json"] or "[]")
        if warnings:
            existing.extend(warnings)
        conn.execute("UPDATE rfp_runs SET status=?, warnings_json=? WHERE run_id=?", (status, json.dumps(existing), run_id))


def save_scoring_results(run_id: str, scored_suppliers: list[dict]) -> None:
    with get_connection() as conn:
        for supplier in scored_suppliers:
            conn.execute(
                "UPDATE supplier_results SET absolute_score=?, ppi=?, rank=? WHERE supplier_result_id=? AND run_id=?",
                (supplier["absolute_score"], supplier["ppi"], supplier["rank"], supplier["supplier_result_id"], run_id),
            )
            for metric in supplier["criterion_metrics"]:
                conn.execute(
                    """UPDATE criterion_results SET benchmark_score=?, gap=?, relative_performance=?, weighted_ppi_contribution=?
                       WHERE supplier_result_id=? AND criterion_id=? AND run_id=?""",
                    (metric["benchmark_score"], metric["gap"], metric["relative_performance"], metric["weighted_ppi_contribution"],
                     supplier["supplier_result_id"], metric["criterion_id"], run_id),
                )


def list_runs(limit: int = 50) -> list[dict]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM rfp_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_leaderboard(run_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier_results WHERE run_id=? ORDER BY CASE WHEN rank IS NULL THEN 1 ELSE 0 END, rank, supplier_name COLLATE NOCASE",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_supplier_scorecard(supplier_result_id: int) -> dict:
    with get_connection() as conn:
        supplier = conn.execute("SELECT * FROM supplier_results WHERE supplier_result_id=?", (supplier_result_id,)).fetchone()
        if not supplier:
            raise ValueError("Supplier scorecard not found.")
        metrics = conn.execute(
            "SELECT * FROM criterion_results WHERE supplier_result_id=? ORDER BY criterion_id", (supplier_result_id,)
        ).fetchall()
        return {"supplier": dict(supplier), "criteria": [dict(r) for r in metrics]}


def export_run_json(run_id: str) -> dict:
    context = get_run_context(run_id)
    with get_connection() as conn:
        suppliers = conn.execute("SELECT * FROM supplier_results WHERE run_id=? ORDER BY COALESCE(rank,999999), supplier_name", (run_id,)).fetchall()
        output = []
        for supplier in suppliers:
            row = dict(supplier)
            criteria = conn.execute("SELECT * FROM criterion_results WHERE supplier_result_id=? ORDER BY criterion_id", (row["supplier_result_id"],)).fetchall()
            output.append({
                "supplier_name": row["supplier_name"], "submission_date": row["submission_date"],
                "experience_rating": row["experience_rating"], "absolute_score": row["absolute_score"],
                "ppi": row["ppi"], "rank": row["rank"], "overall_summary": row["overall_summary"],
                "risks": json.loads(row["risks_json"] or "[]"), "warnings": json.loads(row["warnings_json"] or "[]"),
                "usage": json.loads(row["usage_json"] or "{}"),
                "criteria": [dict(c) for c in criteria],
            })
        return {
            "rfp_run_id": run_id, "created_at": context["run"]["created_at"], "status": context["run"]["status"],
            "criteria_snapshot": context["criteria"], "tie_break_rule": context["run"]["tie_break_rule"],
            "warnings": json.loads(context["run"]["warnings_json"] or "[]"), "suppliers": output,
        }
