# Agentic RFP Evaluation & Supplier Ranking

A Streamlit + SQLite application that extracts supplier proposal PDFs, uses OpenRouter to produce evidence-grounded criterion scores, validates and normalizes the model response, and then uses deterministic Python formulas for weighted scores, peer benchmarks, PPI and ranking.

## 1. Project structure

```text
RFP_Agentic_Evaluation_Complete/
├── app.py
├── pages/
│   ├── 1_Criteria.py
│   ├── 2_Evaluate_Suppliers.py
│   ├── 3_Leaderboard.py
│   └── 4_Run_Details.py
├── rfp/
│   ├── agents/
│   │   ├── evaluation_agent.py
│   │   └── orchestrator.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── repository.py
│   │   └── schema.sql
│   ├── models/schemas.py
│   ├── services/
│   │   ├── scoring_service.py
│   │   ├── benchmarking_service.py
│   │   ├── ranking_service.py
│   │   └── run_service.py
│   └── tools/
│       ├── pdf_reader.py
│       ├── prompt_builder.py
│       └── response_validator.py
├── scripts/
│   ├── init_db.py
│   ├── verify_db.py
│   └── test_apex_evaluation.py
├── tests/
├── sample_data/rfps/       # Six synthetic proposal PDFs
├── data/                   # Local SQLite database is created here
├── outputs/                # Run JSON exports
├── requirements.txt
└── .env.example
```

## 2. Windows PowerShell setup

Open PowerShell in the extracted project folder (the folder containing `app.py`).

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

In `.env`, replace the placeholder with your own OpenRouter key:

```ini
OPENROUTER_API_KEY=your_actual_openrouter_api_key
OPENROUTER_MODEL=google/gemini-3.1-flash-lite
OPENROUTER_SITE_URL=http://localhost:8501
OPENROUTER_APP_NAME=Agentic RFP Evaluation
```

Never paste your API key into chat, source files, screenshots, or a public repository. The real `.env` is excluded from the ZIP and `.gitignore`.

## 3. Initialize and verify SQLite

```powershell
python scripts/init_db.py
python scripts/verify_db.py
```

The default active criteria are Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, and Support & Experience 10%. Their active weights must total 100%. Existing databases are migrated to add the JSON result / usage columns without deleting their saved upload runs.

## 4. Test Apex without using OpenRouter credits

This is an offline wiring test only. It does not claim to assess Apex's actual proposal merit.

```powershell
python scripts/test_apex_evaluation.py --mock
```

Expected: a new Apex-only run is created, the PDF is extracted, the mock evaluator returns a complete five-criterion response, it is normalized, scoring/benchmarking/ranking runs, and an output JSON is written under `outputs/`.

Run the automated tests:

```powershell
pytest
```

## 5. Run the real Apex AI evaluation (Step 6)

After entering a valid OpenRouter API key in `.env`:

```powershell
python scripts/test_apex_evaluation.py
```

This creates a fresh Apex-only run and sends the proposal text to the configured OpenRouter model using Chat Completions with `response_format` JSON Schema. It normalizes the response and stores the scorecard in SQLite. The full JSON output is written to `outputs/`.

You can test a different PDF:

```powershell
python scripts/test_apex_evaluation.py --pdf "C:\path\to\supplier.pdf" --supplier-name "Supplier Name" --experience-rating 7
```

You can also evaluate an existing run by passing `--run-id RFP-...`.

## 6. Run the Streamlit application

```powershell
streamlit run app.py
```

Use the pages in the left sidebar:
- **Criteria:** inspect and edit criteria / weights. Active weights must remain 100%.
- **Evaluate Suppliers:** upload multiple PDFs, provide submission date and experience rating, create a run, and execute OpenRouter evaluation.
- **Leaderboard:** view absolute weighted scores, PPI and final rank.
- **Run Details:** inspect scorecards, evidence, justifications, warnings and download complete run JSON.

For Streamlit Community Cloud, add `OPENROUTER_API_KEY` and (optionally) `OPENROUTER_MODEL` under App settings → Secrets. Do not deploy the local database file; SQLite persistence on hosted ephemeral filesystems may not be durable across restarts.

## 7. Formulas and ranking rules

**Absolute weighted score (0–100):**

`SUM((criterion_score / criterion_max_score) × criterion_weight)`

**Criterion benchmark:** highest validated criterion score among suppliers successfully evaluated in that run.

**Criterion gap:** `supplier_score - benchmark_score` (zero for the benchmark leader; otherwise negative or zero).

**Relative performance:** `(supplier_score / benchmark_score) × 100`. When the benchmark is zero, the implementation assigns 100% to every supplier for that criterion because every peer scored zero and there is no relative separation.

**Peer Performance Index (PPI):** weighted average of criterion relative-performance percentages. It is on a 0–100 scale because no supplier can exceed the best observed peer score on a criterion.

**Tie-break order:** (1) higher PPI, (2) earlier submission date, (3) higher historical experience rating, (4) supplier name ascending. Ranks are assigned sequentially after sorting.

A one-supplier test run will have PPI 100% by construction, because that supplier is also the benchmark for every criterion. Use the six-supplier batch for meaningful peer comparisons.

## 8. Important safeguards / assumptions

- The model assigns criterion scores and produces justifications/evidence only. Python performs arithmetic, benchmarking, PPI and ranking.
- The model is instructed to use only proposal evidence. Evidence and AI judgments still require human review before a procurement decision.
- Missing criterion results are filled with score zero and warnings; invalid scores are clipped to the configured 0-to-maximum range; duplicate and unknown criterion IDs are ignored with warnings.
- Supplier-level failures do not stop other suppliers. A run with one or more supplier failures is marked `failed`, while successful scorecards and partial ranking remain persisted for diagnosis.
- PDFs must contain selectable text. Scanned image-only PDFs need OCR, which is not included in this build.
- The included six proposals are synthetic learning examples, not real supplier submissions.
