from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rfp.database.connection import DB_PATH
from rfp.database.repository import get_active_criteria, initialize_database


if __name__ == "__main__":
    initialize_database()
    active = get_active_criteria()
    print("DATABASE INITIALIZED")
    print(f"Database: {DB_PATH}")
    for item in active:
        print(f"{item['criterion_name']}: {item['weight']}% (max {item['max_score']})")
    total = sum(float(item["weight"]) for item in active)
    print(f"Active weight total: {total:.2f}%")
    if round(total, 2) != 100:
        raise SystemExit("ERROR: active criterion weights must total 100%.")
