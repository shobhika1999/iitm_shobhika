from __future__ import annotations

import streamlit as st

from rfp.database.repository import get_active_criteria, initialize_database, list_runs

st.set_page_config(page_title="Agentic RFP Evaluator", page_icon="📊", layout="wide")
initialize_database()

st.title("Agentic RFP Evaluation & Supplier Ranking")
st.caption("AI evaluates proposal evidence. Python performs scoring, peer benchmarking and ranking.")

criteria = get_active_criteria()
runs = list_runs(limit=10)
col1, col2, col3 = st.columns(3)
col1.metric("Active criteria", len(criteria))
col2.metric("Combined weight", f"{sum(float(c['weight']) for c in criteria):.1f}%")
col3.metric("Recent runs", len(runs))

st.subheader("Workflow")
st.markdown(
    "1. **Criteria:** confirm active criteria and weights total 100%.\n"
    "2. **Evaluate Suppliers:** upload PDFs, enter supplier metadata, create a run, and call OpenRouter.\n"
    "3. **Leaderboard:** compare absolute weighted scores and Peer Performance Index (PPI).\n"
    "4. **Run Details:** inspect evidence, justifications, warnings, tie-break rules and download JSON."
)
if round(sum(float(c["weight"]) for c in criteria), 2) != 100:
    st.error("Active criteria weights must total exactly 100%. Correct them on the Criteria page before creating a run.")

st.subheader("Recent runs")
if runs:
    st.dataframe(
        [{"Run ID": r["run_id"], "Created": r["created_at"], "Status": r["status"], "Suppliers": r["supplier_count"]} for r in runs],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No runs yet. Open Evaluate Suppliers to upload the first proposal.")

st.caption("Procurement decision support only. Review supplier evidence and all AI-generated scores before taking a purchasing decision.")
