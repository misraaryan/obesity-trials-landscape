"""
Step 2: Turn the raw API data into a clean SQLite database.

Input:  data/raw/studies.jsonl            (from 01_download.py)
Output: data/processed/obesity_trials.db  (SQLite database, 4 tables)
        data/processed/*.csv              (same tables as CSV, for Tableau)

Tables
  trials         one row per study (status, phase, dates, sponsor, enrollment, drug class)
  interventions  one row per intervention in a study (drug, behavioural, device...)
  locations      one row per trial site (facility, city, country)
  conditions     one row per condition listed on a study

Run from the project folder:
    python src/02_build_db.py
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/raw/studies.jsonl")
OUT_DIR = Path("data/processed")
DB_FILE = OUT_DIR / "obesity_trials.db"

# ---------------------------------------------------------------------------
# Drug class rules: if any of these words appears in an intervention's name
# (or its other names), the intervention gets that class.
# Order matters: combinations are checked before single agents.
# ---------------------------------------------------------------------------
#
# Besides named drugs, four official naming stems (INN stems) identify the class
# of new drugs: "-glipron" = oral small-molecule GLP-1 agonist, "-dutide" = GLP-1/glucagon
# dual agonist, "-lintide" = amylin analogue, "-glutide" = GLP-1 analogue
# (except the GLP-2 drugs listed in NOT_GLP1 below).
# Company code names are included only where the generic name is publicly confirmed.
DRUG_CLASS_RULES = [
    ("Amylin + GLP-1 combination", ["cagrisema", "cagrilintide/semaglutide", "cagrilintide and semaglutide"]),
    ("GLP-1/amylin co-agonist", ["amycretin", "zenagamtide", "zengamatide", "nnc0487-0111"]),
    ("GLP-1/GIP/glucagon triple agonist", ["retatrutide", "ly3437943"]),
    ("GIP/GLP-1 dual agonist", ["tirzepatide", "ly3298176", "mounjaro", "zepbound", "vk2735"]),
    ("GLP-1/glucagon dual agonist", ["dutide", "bi 456906", "ibi362", "medi0382"]),
    ("GLP-1 RA + GIPR antagonist", ["maridebart", "amg 133", "amg133"]),
    ("Oral small-molecule GLP-1", ["glipron", "ly3502970", "pf-06882961", "pf-07081532"]),
    ("Amylin analogue", ["lintide", "nnc0174-0833"]),
    ("GLP-1 receptor agonist", ["glutide", "exenatide", "lixisenatide", "efpeglenatide",
                                "wegovy", "ozempic", "rybelsus", "saxenda", "victoza", "xw003"]),
    ("Older anti-obesity drug", ["orlistat", "phentermine", "topiramate", "naltrexone", "bupropion",
                                 "lorcaserin", "sibutramine"]),
    ("MC4R agonist", ["setmelanotide"]),
]


NOT_GLP1 = ["teduglutide", "glepaglutide", "apraglutide"]   # GLP-2 drugs for short bowel syndrome


def classify_drug(text):
    """Return the drug class for an intervention name, or None if no rule matches."""
    text = text.lower()
    for word in NOT_GLP1:
        text = text.replace(word, "")
    for drug_class, keywords in DRUG_CLASS_RULES:
        if any(k in text for k in keywords):
            return drug_class
    return None


def year_from(date_string):
    """'2023-05' or '2023-05-14' -> 2023. Missing dates -> None."""
    if not date_string:
        return None
    return int(date_string[:4])


def phase_label(phases):
    """['PHASE2', 'PHASE3'] -> 'PHASE2/PHASE3'. No phase (e.g. observational) -> 'NA'."""
    if not phases:
        return "NA"
    return "/".join(sorted(phases))


def parse_study(study):
    """Pull the fields we need out of one study's nested JSON."""
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    arms = p.get("armsInterventionsModule", {})
    conds = p.get("conditionsModule", {})
    contacts = p.get("contactsLocationsModule", {})

    nct_id = ident.get("nctId")

    # --- interventions ---
    interventions = []
    for iv in arms.get("interventions", []) or []:
        name = iv.get("name", "")
        all_names = " ".join([name] + (iv.get("otherNames") or []))
        interventions.append({
            "nct_id": nct_id,
            "intervention_type": iv.get("type"),
            "intervention_name": name,
            "drug_class": classify_drug(all_names) if iv.get("type") in ("DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT") else None,
        })

    # Trial-level drug class: first class found, in rule order (so combinations win)
    found = {iv["drug_class"] for iv in interventions if iv["drug_class"]}
    # Cagrilintide and semaglutide listed as two separate interventions = the CagriSema combination
    if {"Amylin analogue", "GLP-1 receptor agonist"} <= found:
        found.add("Amylin + GLP-1 combination")
    trial_class = next((c for c, _ in DRUG_CLASS_RULES if c in found), None)
    if trial_class is None:
        types = {iv["intervention_type"] for iv in interventions}
        if types & {"DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT"}:
            trial_class = "Other or unclassified drug"
        elif interventions:
            trial_class = "Non-drug (" + ", ".join(sorted(t.title() for t in types if t)) + ")"
        else:
            trial_class = "No intervention listed"

    # --- trial row ---
    trial = {
        "nct_id": nct_id,
        "title": ident.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "study_type": design.get("studyType"),
        "phase": phase_label(design.get("phases")),
        "start_year": year_from(status.get("startDateStruct", {}).get("date")),
        "completion_year": year_from(status.get("completionDateStruct", {}).get("date")),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "lead_sponsor": sponsor.get("name"),
        "sponsor_class": sponsor.get("class"),   # INDUSTRY, OTHER (mostly academic), NIH, ...
        "has_results": bool(study.get("hasResults", False)),
        "drug_class": trial_class,
    }

    # --- locations and conditions ---
    locations = [{
        "nct_id": nct_id,
        "facility": loc.get("facility"),
        "city": loc.get("city"),
        "country": loc.get("country"),
    } for loc in contacts.get("locations", []) or []]

    conditions = [{"nct_id": nct_id, "condition": c} for c in conds.get("conditions", []) or []]

    return trial, interventions, locations, conditions


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trials, interventions, locations, conditions = [], [], [], []
    with RAW_FILE.open(encoding="utf-8") as f:
        for line in f:
            t, i, l, c = parse_study(json.loads(line))
            trials.append(t)
            interventions.extend(i)
            locations.extend(l)
            conditions.extend(c)

    tables = {
        "trials": pd.DataFrame(trials).drop_duplicates("nct_id").astype(
            {"start_year": "Int64", "completion_year": "Int64", "enrollment": "Int64"}),
        "interventions": pd.DataFrame(interventions),
        "locations": pd.DataFrame(locations),
        "conditions": pd.DataFrame(conditions),
    }

    if DB_FILE.exists():
        DB_FILE.unlink()                      # rebuild from scratch every run
    with sqlite3.connect(DB_FILE) as con:
        for name, df in tables.items():
            df.to_sql(name, con, index=False)
            df.to_csv(OUT_DIR / f"{name}.csv", index=False)
            print(f"{name}: {len(df):,} rows")

    print(f"Database written to {DB_FILE}")


if __name__ == "__main__":
    main()
