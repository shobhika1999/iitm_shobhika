from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rfp.database.connection import DB_PATH, get_connection
from rfp.database.repository import initialize_database

initialize_database()
with get_connection() as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print(f"Database: {DB_PATH}")
    print("Tables:")
    for item in tables:
        print(" -", item["name"])
    print("\nRuns:")
    for item in conn.execute("SELECT run_id,status,supplier_count FROM rfp_runs ORDER BY created_at DESC LIMIT 10"):
        print(dict(item))
