"""
Step 4: Add India's own trial registry (CTRI) to the database.

Why: ClinicalTrials.gov misses trials that are registered only in India. CTRI (ctri.nic.in)
is India's mandatory registry. CTRI's own search sits behind a CAPTCHA, so the records were
collected from the WHO International Clinical Trials Registry Platform (ICTRP,
trialsearch.who.int), which mirrors CTRI.

Search used on ICTRP (18 Nov 2026):
  condition = "obesity OR overweight", recruitment status = ALL, country of recruitment = India
  -> 1,065 trials; 930 of them have a CTRI main ID.

Input:  data/raw/ictrp_india_details.json.gz   (one record per CTRI trial; no personal contact data)
Output: table "ctri_trials" in data/processed/obesity_trials.db (+ CSV)

Run from the project folder:
    python src/04_india_registry.py
"""

import gzip
import importlib.util
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/raw/ictrp_india_details.json.gz")
DB_FILE = Path("data/processed/obesity_trials.db")
CSV_FILE = Path("data/processed/ctri_trials.csv")

# Re-use the drug-class rules from step 2 so both registries are classified the same way
_spec = importlib.util.spec_from_file_location("build_db", Path(__file__).with_name("02_build_db.py"))
build_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_db)

MULTINATIONALS = ["novo nordisk", "eli lilly", "lilly", "astrazeneca", "boehringer", "roche", "pfizer",
                  "amgen", "sanofi", "merck", "glaxo", "gsk", "novartis", "bayer", "takeda", "abbott",
                  "johnson", "janssen", "regeneron", "viking", "structure therapeutics"]

COMPANY_WORDS = r"\b(ltd|limited|pvt|private|pharma|pharmaceuticals?|laboratories|labs|lifesciences|life sciences|" \
                r"inc|llc|a/s|gmbh|corporation|corp|company|healthcare|biotech|biologics|therapeutics|cro)\b"

MODALITY_RULES = [
    ("Traditional medicine (AYUSH)", r"ayurved|unani|homoeopath|homeopath|siddha|sthaulya|medoroga|"
                                     r"churna|kwath|vati|basti|virechana|lekhana|udvartana|naturopathy"),
    ("Yoga / exercise", r"\byoga\b|exercise|physical activity|training|aerobic|walking|pranayama"),
    ("Diet / lifestyle", r"\bdiet|dietary|lifestyle|counsel|nutrition|fasting|calorie|behaviou?r"),
    ("Surgery / procedure", r"bariatric|sleeve|gastrectomy|bypass|surgery|surgical|balloon|endoscop"),
    ("Supplement / nutraceutical", r"supplement|nutraceutical|probiotic|extract|herbal|capsule of"),
]


def sponsor_type(name):
    n = name.lower()
    if any(m in n for m in MULTINATIONALS):
        return "Multinational pharma"
    if re.search(COMPANY_WORDS, n):
        return "Indian or other company"
    return "Academic / hospital / government"


def year_from_ddmmyyyy(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def main():
    with gzip.open(RAW_FILE, "rt", encoding="utf-8") as f:
        records = json.load(f)
    rows = []
    for r in records:
        if r.get("error"):
            continue
        text = " ".join([r["public_title"], r["scientific_title"], " ".join(r["interventions"])])
        drug_class = build_db.classify_drug(text)
        if drug_class:
            modality = "Anti-obesity drug (classified)"
        else:
            modality = next((label for label, pat in MODALITY_RULES if re.search(pat, text, re.I)), None)
            if modality is None:
                # Trials with a formal phase that matched nothing above are usually drug studies
                modality = "Other drug or product" if re.search(r"phase\s*[1-4]", r["phase"], re.I) else "Other / unclear"
        nct_ids = sorted(set(re.findall(r"NCT\d{8}", " ".join(r["secondary_ids"]))))
        rows.append({
            "ctri_id": r["id"],
            "title": r["public_title"],
            "sponsor": r["sponsor"],
            "sponsor_type": sponsor_type(r["sponsor"]),
            "registration_year": year_from_ddmmyyyy(r["date_registration"]),
            "study_type": r["study_type"],
            "phase": r["phase"],
            "recruitment_status": r["recruitment_status"],
            "target_size": pd.to_numeric(r["target_size"], errors="coerce"),
            "n_countries": len(r["countries"]),
            "india_only": r["countries"] == ["India"],
            "modality": modality,
            "drug_class": drug_class,
            "also_on_ctgov": bool(nct_ids),
            "nct_ids": ",".join(nct_ids),
        })

    df = pd.DataFrame(rows).astype({"registration_year": "Int64"})
    with sqlite3.connect(DB_FILE) as con:
        df.to_sql("ctri_trials", con, index=False, if_exists="replace")
    df.to_csv(CSV_FILE, index=False)
    print(f"ctri_trials: {len(df):,} rows written to {DB_FILE} and {CSV_FILE}")


if __name__ == "__main__":
    main()
