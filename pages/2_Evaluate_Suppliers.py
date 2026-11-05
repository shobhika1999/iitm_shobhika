from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from rfp.database.repository import get_active_criteria, list_runs, save_evaluation_run
from rfp.services.run_service import run_evaluation
from rfp.tools.pdf_reader import extract_pdf_text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Evaluate Suppliers", page_icon="📄", layout="wide")
st.title("Upload & Evaluate Supplier Proposals")

criteria = get_active_criteria()
active_weight = sum(float(c["weight"]) for c in criteria)
if not criteria or round(active_weight, 2) != 100:
    st.error(f"Active criteria must be configured and total 100%. Current total: {active_weight:.2f}%.")
    st.stop()

st.caption(f"Current criteria snapshot: {len(criteria)} active criteria, total weight {active_weight:.2f}%.")
uploads = st.file_uploader("Upload supplier RFP PDFs", type=["pdf"], accept_multiple_files=True)

if uploads:
    metadata = []
    st.subheader("Supplier metadata")
    for idx, file in enumerate(uploads):
        default_name = file.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        with st.expander(f"{idx + 1}. {file.name}", expanded=idx == 0):
            name = st.text_input("Supplier name", value=default_name, key=f"supplier_name_{idx}")
            col1, col2 = st.columns(2)
            with col1:
                submission_date = st.date_input("Submission date", value=date.today(), key=f"submission_date_{idx}")
            with col2:
                experience = st.number_input("Historical experience rating (1-10)", min_value=1.0, max_value=10.0, value=5.0, step=0.5, key=f"experience_{idx}")
            metadata.append({"supplier_name": name.strip(), "submission_date": submission_date.isoformat(), "experience_rating": experience, "file": file})

    if st.button("Extract PDFs & create evaluation batch", type="primary"):
        names = [m["supplier_name"].casefold() for m in metadata]
        if any(not n for n in names) or len(names) != len(set(names)):
            st.error("Supplier names must be non-empty and unique within the batch.")
        else:
            documents = []
            errors = []
            progress = st.progress(0)
            for idx, item in enumerate(metadata, start=1):
                try:
                    result = extract_pdf_text(item["file"].getvalue())
                    documents.append({
                        "supplier_name": item["supplier_name"],
                        "submission_date": item["submission_date"],
                        "experience_rating": item["experience_rating"],
                        "file_name": item["file"].name,
                        "page_count": result["page_count"],
                        "extracted_text": result["extracted_text"],
                        "status": result["status"],
                    })
                    if result["status"] != "SUCCESS":
                        errors.append(f"{item['supplier_name']}: {result['status']}")
                except Exception as exc:
                    documents.append({
                        "supplier_name": item["supplier_name"],
                        "submission_date": item["submission_date"],
                        "experience_rating": item["experience_rating"],
                        "file_name": item["file"].name,
                        "page_count": 0,
                        "extracted_text": "",
                        "status": f"ERROR: {exc}",
                    })
                    errors.append(f"{item['supplier_name']}: {exc}")
                progress.progress(idx / len(metadata))
            try:
                run_id = save_evaluation_run(documents)
                st.session_state["latest_run_id"] = run_id
                st.success(f"Batch created. Run ID: {run_id}")
                st.write({"PDFs": len(documents), "Text extraction successful": sum(d["status"] == "SUCCESS" for d in documents), "Extraction warnings": errors})
            except Exception as exc:
                st.error(f"Could not save batch: {exc}")

st.divider()
st.subheader("Run AI evaluation")
runs = list_runs(limit=50)
run_options = [r["run_id"] for r in runs]
default_run = st.session_state.get("latest_run_id")
if default_run not in run_options:
    default_run = run_options[0] if run_options else None
if not run_options:
    st.info("Create an upload batch above before starting evaluation.")
else:
    selected_run = st.selectbox("Select a saved batch", run_options, index=run_options.index(default_run) if default_run in run_options else 0)
    st.caption("The AI evaluates each supplier independently. Python then calculates the weighted score, peer benchmarks, PPI and rank.")
    if st.button("Start OpenRouter evaluation", type="primary", key="run_openrouter"):
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        try:
            if not api_key:
                try:
                    api_key = str(st.secrets.get("OPENROUTER_API_KEY", "")).strip()
                except Exception:
                    api_key = ""
            if not api_key:
                st.error("OpenRouter API key is missing. Add OPENROUTER_API_KEY to your local .env file or Streamlit secrets.")
            else:
                os.environ["OPENROUTER_API_KEY"] = api_key
                progress = st.progress(0)
                status = st.empty()
                def on_progress(index, total, name, message):
                    progress.progress(min(index / max(total, 1), 1.0))
                    status.write(f"{index}/{total} — {name}: {message}")
                with st.spinner("Evaluating supplier proposals with OpenRouter..."):
                    result = run_evaluation(selected_run, progress_callback=on_progress)
                if result["status"] == "completed":
                    st.success(f"Evaluation completed: {result['evaluated_count']} supplier(s).")
                else:
                    st.warning(f"Evaluation finished with failures: {result['evaluated_count']} succeeded, {result['failed_count']} failed. See Run Details.")
                st.dataframe(result["leaderboard"], use_container_width=True, hide_index=True)
        except Exception as exc:
            st.exception(exc)
