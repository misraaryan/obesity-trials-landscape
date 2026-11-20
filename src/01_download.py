"""
Step 1: Download every obesity / overweight study from ClinicalTrials.gov.

Source: ClinicalTrials.gov API v2 (free, no key needed)
Docs:   https://clinicaltrials.gov/data-api/api

Output: data/raw/studies.jsonl  (one study per line, raw JSON as returned by the API)

Run from the project folder:
    python src/01_download.py
"""

import json
import time
from pathlib import Path

import requests

API_URL = "https://clinicaltrials.gov/api/v2/studies"
CONDITION_QUERY = "obesity OR overweight"   # same search you would type on the website
PAGE_SIZE = 1000                            # API maximum per request

# Only the parts of each record the analysis uses (keeps the file at ~60 MB instead of several hundred)
FIELDS = ",".join([
    "protocolSection.identificationModule",
    "protocolSection.statusModule",
    "protocolSection.designModule",
    "protocolSection.sponsorCollaboratorsModule",
    "protocolSection.armsInterventionsModule",
    "protocolSection.conditionsModule",
    "protocolSection.contactsLocationsModule",
    "hasResults",
])

OUT_FILE = Path("data/raw/studies.jsonl")


def download_all_studies():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    params = {
        "query.cond": CONDITION_QUERY,
        "pageSize": PAGE_SIZE,
        "countTotal": "true",   # ask the API to tell us the total number of matches
        "fields": FIELDS,
        "format": "json",
    }

    total_saved = 0
    page = 1

    with OUT_FILE.open("w", encoding="utf-8") as f:
        while True:
            response = requests.get(API_URL, params=params, timeout=60)
            response.raise_for_status()          # stop with an error if the request failed
            data = response.json()

            if page == 1:
                print(f"Total studies matching '{CONDITION_QUERY}': {data.get('totalCount')}")

            studies = data.get("studies", [])
            for study in studies:
                f.write(json.dumps(study) + "\n")
            total_saved += len(studies)
            print(f"Page {page}: saved {len(studies)} studies (running total {total_saved})")

            # The API returns a nextPageToken until we reach the last page
            next_token = data.get("nextPageToken")
            if not next_token:
                break
            params["pageToken"] = next_token
            page += 1
            time.sleep(0.5)                      # be polite to the server

    print(f"Done. {total_saved} studies written to {OUT_FILE}")


if __name__ == "__main__":
    download_all_studies()
