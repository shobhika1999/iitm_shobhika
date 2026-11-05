from __future__ import annotations

import streamlit as st

from rfp.database.repository import get_all_criteria, save_criteria

st.set_page_config(page_title="Evaluation Criteria", page_icon="⚖️", layout="wide")
st.title("Evaluation Criteria")
st.write("Weights are used by Python for deterministic scoring. The LLM receives criterion descriptions and maximum scores, not criterion weights.")

criteria = get_all_criteria()
if not criteria:
    st.warning("No criteria are configured. Initialize the database first.")
    st.stop()

with st.form("criteria_form"):
    edited = st.data_editor(
        [{
            "criterion_id": int(c["criterion_id"]),
            "criterion_name": c["criterion_name"],
            "description": c["description"],
            "weight": float(c["weight"]),
            "max_score": float(c["max_score"]),
            "is_active": bool(c["is_active"]),
        } for c in criteria],
        column_config={
            "criterion_id": st.column_config.NumberColumn("ID", disabled=True),
            "criterion_name": st.column_config.TextColumn("Criterion", required=True),
            "description": st.column_config.TextColumn("Description", required=True, width="large"),
            "weight": st.column_config.NumberColumn("Weight (%)", min_value=0.01, max_value=100.0, step=0.5),
            "max_score": st.column_config.NumberColumn("Maximum score", min_value=0.1, max_value=100.0, step=0.5),
            "is_active": st.column_config.CheckboxColumn("Active"),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )
    submitted = st.form_submit_button("Save criteria", type="primary")

if submitted:
    try:
        save_criteria(edited.to_dict(orient="records"))
        st.success("Criteria saved successfully.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))

active = [c for c in criteria if c["is_active"]]
weight_total = sum(float(c["weight"]) for c in active)
st.metric("Current active weight total", f"{weight_total:.2f}%")
if round(weight_total, 2) == 100:
    st.success("Weight validation passed.")
else:
    st.error("Active weights must total 100% before a batch can be created.")
