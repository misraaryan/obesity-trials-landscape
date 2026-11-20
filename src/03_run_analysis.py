"""
Step 3: Run every query in sql/analysis.sql, print the results and save each as a CSV.

Input:  data/processed/obesity_trials.db
Output: outputs/<query_name>.csv

Run from the project folder:
    python src/03_run_analysis.py
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE = Path("data/processed/obesity_trials.db")
SQL_FILE = Path("sql/analysis.sql")
OUT_DIR = Path("outputs")


def load_queries(sql_text):
    """Split the .sql file into {name: query} using the '-- name:' markers."""
    # A marker is a line that starts with "-- name: <query_name>"
    parts = re.split(r"^-- name:\s*(\w+)\s*$", sql_text, flags=re.MULTILINE)
    # parts = [header, name1, body1, name2, body2, ...]
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def main():
    OUT_DIR.mkdir(exist_ok=True)
    queries = load_queries(SQL_FILE.read_text(encoding="utf-8"))

    pd.set_option("display.width", 160)
    with sqlite3.connect(DB_FILE) as con:
        for name, query in queries.items():
            df = pd.read_sql_query(query, con)
            df.to_csv(OUT_DIR / f"{name}.csv", index=False)
            print(f"\n=== {name} ({len(df)} rows) ===")
            print(df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
