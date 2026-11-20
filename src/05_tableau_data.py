"""
Step 5: Build one tidy file for the Tableau Public dashboard.

Input:  outputs/q03, q05, q11, q15 CSVs and the ctri_trials table
Output: data/tableau/dashboard_data.csv

Long format: one row per value. The "chart" column says which dashboard chart a row
belongs to, so every Tableau sheet uses the same data source with a filter on "chart".

Run from the project folder (after 03_run_analysis.py):
    python src/05_tableau_data.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE = Path("data/processed/obesity_trials.db")
OUT_FILE = Path("data/tableau/dashboard_data.csv")


def main():
    rows = []

    # 1. Industry share of new interventional trials, 2010-2025 (2026 left out: it includes planned trials)
    q5 = pd.read_csv("outputs/q05_industry_share_by_year.csv")
    for r in q5[q5.start_year <= 2025].itertuples():
        rows.append(dict(chart="1 Industry share", label=str(r.start_year),
                         series="Industry share of new trials (%)", year=r.start_year, value=r.industry_pct))
        rows.append(dict(chart="1 Industry share", label=str(r.start_year),
                         series="New interventional trials", year=r.start_year, value=r.trials))

    # 2. Drug class momentum: trials per class in three periods
    q3 = pd.read_csv("outputs/q03_drug_class_by_period.csv")
    for r in q3.itertuples():
        for col, period in [("trials_2010_2017", "2010-2017"), ("trials_2018_2021", "2018-2021"),
                            ("trials_2022_on", "2022 onward")]:
            rows.append(dict(chart="2 Drug class momentum", label=r.drug_class, series=period,
                             year=None, value=getattr(r, col)))

    # 3. Home-grown vs imported industry drug trials by country
    q15 = pd.read_csv("outputs/q15_india_vs_china_innovation.csv")
    for r in q15.itertuples():
        rows.append(dict(chart="3 Home-grown vs imported", label=r.country,
                         series="Run only in this country", year=None, value=r.domestic_only))
        rows.append(dict(chart="3 Home-grown vs imported", label=r.country,
                         series="Multi-country", year=None, value=r.industry_drug_trials - r.domestic_only))

    # 4. What obesity trials registered in India test
    q11 = pd.read_csv("outputs/q11_ctri_modality_mix.csv")
    for r in q11.itertuples():
        rows.append(dict(chart="4 What India tests", label=r.modality,
                         series="Interventional trials in CTRI", year=None, value=r.trials))

    # 5. Indian companies' semaglutide trials in CTRI
    with sqlite3.connect(DB_FILE) as con:
        g = pd.read_sql("""SELECT sponsor, registration_year, phase FROM ctri_trials
                           WHERE sponsor_type = 'Indian or other company'
                             AND LOWER(title) LIKE '%semaglutide%'
                           ORDER BY registration_year, sponsor""", con)
    for r in g.itertuples():
        rows.append(dict(chart="5 Indian semaglutide Phase 3", label=r.sponsor, series=r.phase,
                         year=r.registration_year, value=1))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).astype({"year": "Int64"}).to_csv(OUT_FILE, index=False)
    print(f"{len(rows)} rows written to {OUT_FILE}")


if __name__ == "__main__":
    main()
