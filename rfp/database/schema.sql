CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    weight REAL NOT NULL CHECK (weight > 0 AND weight <= 100),
    max_score REAL NOT NULL DEFAULT 10 CHECK (max_score > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'evaluating', 'completed', 'failed')),
    criteria_total_weight REAL NOT NULL DEFAULT 0,
    supplier_count INTEGER NOT NULL DEFAULT 0,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    tie_break_rule TEXT
);

CREATE TABLE IF NOT EXISTS run_criteria_snapshot (
    run_id TEXT NOT NULL,
    criterion_id INTEGER NOT NULL,
    criterion_name TEXT NOT NULL,
    description TEXT NOT NULL,
    weight REAL NOT NULL,
    max_score REAL NOT NULL,
    PRIMARY KEY (run_id, criterion_id),
    FOREIGN KEY (run_id) REFERENCES rfp_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS supplier_results (
    supplier_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    submission_date TEXT NOT NULL,
    experience_rating REAL NOT NULL CHECK (experience_rating >= 1 AND experience_rating <= 10),
    file_name TEXT NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0,
    absolute_score REAL,
    ppi REAL,
    rank INTEGER,
    overall_summary TEXT,
    risks_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    result_json TEXT,
    usage_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (run_id, supplier_name),
    FOREIGN KEY (run_id) REFERENCES rfp_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS criterion_results (
    criterion_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_result_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    criterion_id INTEGER NOT NULL,
    criterion_name TEXT NOT NULL,
    score REAL NOT NULL,
    max_score REAL NOT NULL,
    justification TEXT NOT NULL,
    evidence TEXT NOT NULL,
    benchmark_score REAL,
    gap REAL,
    relative_performance REAL,
    weighted_ppi_contribution REAL,
    UNIQUE (supplier_result_id, criterion_id),
    FOREIGN KEY (supplier_result_id) REFERENCES supplier_results(supplier_result_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id, criterion_id) REFERENCES run_criteria_snapshot(run_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS supplier_documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_result_id INTEGER NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0,
    extracted_text TEXT NOT NULL DEFAULT '',
    extraction_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_result_id) REFERENCES supplier_results(supplier_result_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_supplier_results_run ON supplier_results(run_id);
CREATE INDEX IF NOT EXISTS idx_criterion_results_supplier ON criterion_results(supplier_result_id);
