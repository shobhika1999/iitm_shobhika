from __future__ import annotations

import streamlit as st

from rfp.database.repository import get_leaderboard, list_runs

st.set_page_config(page_title="Supplier Leaderboard", page_icon="🏆", layout="wide")
st.title("Supplier Leaderboard")
runs = list_runs(limit=100)
if not runs:
    st.info("No evaluation runs are available yet.")
    st.stop()
run_ids = [r["run_id"] for r in runs]
selected = st.selectbox("Evaluation run", run_ids)
run = next(r for r in runs if r["run_id"] == selected)
st.caption(f"Status: {run['status']} | Created: {run['created_at']} | Suppliers: {run['supplier_count']}")
rows = get_leaderboard(selected)
if not rows:
    st.info("This run has no supplier records.")
else:
    st.dataframe(
        [{
            "Rank": r["rank"], "Supplier": r["supplier_name"],
            "Absolute weighted score": r["absolute_score"], "PPI (%)": r["ppi"],
            "Submission date": r["submission_date"], "Experience rating": r["experience_rating"],
            "File": r["file_name"],
        } for r in rows],
        use_container_width=True, hide_index=True,
    )
    st.caption("Absolute score = sum((criterion score / maximum score) × criterion weight). PPI is the weighted average of each criterion's relative performance against the best observed peer score.")
