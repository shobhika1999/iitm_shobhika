from __future__ import annotations

import json

import streamlit as st

from rfp.database.repository import export_run_json, get_leaderboard, get_run_context, get_supplier_scorecard, list_runs

st.set_page_config(page_title="Run Details", page_icon="🔎", layout="wide")
st.title("Run Details & Evidence")
runs = list_runs(limit=100)
if not runs:
    st.info("No evaluation runs are available.")
    st.stop()
run_ids = [r["run_id"] for r in runs]
selected = st.selectbox("Select run", run_ids)
context = get_run_context(selected)
run = context["run"]
col1, col2, col3 = st.columns(3)
col1.metric("Run status", run["status"])
col2.metric("Supplier count", run["supplier_count"])
col3.metric("Criteria weight", f"{run['criteria_total_weight']:.2f}%")
st.write("**Run ID:**", selected)
st.write("**Tie-break order:**", run["tie_break_rule"])
run_warnings = json.loads(run["warnings_json"] or "[]")
if run_warnings:
    st.warning("Run warnings")
    for warning in run_warnings:
        st.write(f"- {warning}")

rows = get_leaderboard(selected)
if rows:
    names = [f"{r['supplier_name']} (rank {r['rank'] if r['rank'] is not None else 'not ranked'})" for r in rows]
    selected_index = st.selectbox("Supplier scorecard", range(len(rows)), format_func=lambda i: names[i])
    chosen = rows[selected_index]
    scorecard = get_supplier_scorecard(chosen["supplier_result_id"])
    supplier = scorecard["supplier"]
    st.subheader(supplier["supplier_name"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Absolute score", "—" if supplier["absolute_score"] is None else f"{supplier['absolute_score']:.2f}/100")
    c2.metric("PPI", "—" if supplier["ppi"] is None else f"{supplier['ppi']:.2f}%")
    c3.metric("Final rank", "—" if supplier["rank"] is None else supplier["rank"])
    if supplier["overall_summary"]:
        st.write("**Overall summary**")
        st.write(supplier["overall_summary"])
    risks = json.loads(supplier["risks_json"] or "[]")
    if risks:
        st.write("**Identified risks**")
        for risk in risks:
            st.write(f"- {risk}")
    warnings = json.loads(supplier["warnings_json"] or "[]")
    if warnings:
        st.warning("Supplier validation / execution warnings")
        for warning in warnings:
            st.write(f"- {warning}")
    if scorecard["criteria"]:
        st.subheader("Criterion scorecard")
        st.dataframe([
            {
                "Criterion": c["criterion_name"], "Score": c["score"], "Maximum": c["max_score"],
                "Weight (%)": next((s["weight"] for s in context["criteria"] if s["criterion_id"] == c["criterion_id"]), None),
                "Benchmark": c["benchmark_score"], "Gap": c["gap"],
                "Relative performance (%)": c["relative_performance"],
                "Weighted PPI contribution": c["weighted_ppi_contribution"],
            } for c in scorecard["criteria"]
        ], use_container_width=True, hide_index=True)
        for c in scorecard["criteria"]:
            with st.expander(c["criterion_name"]):
                st.write(f"**Score:** {c['score']} / {c['max_score']}")
                st.write("**Justification**")
                st.write(c["justification"])
                st.write("**Supporting evidence**")
                st.write(c["evidence"])
    else:
        st.info("No criterion evaluation results are stored for this supplier yet.")

payload = export_run_json(selected)
st.download_button(
    "Download complete run JSON",
    data=json.dumps(payload, indent=2, ensure_ascii=False),
    file_name=f"{selected}.json",
    mime="application/json",
)
