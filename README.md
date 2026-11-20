# India in the Global Obesity Drug Race: Trial Site or Innovator?

An analysis of 15,801 obesity and overweight studies on ClinicalTrials.gov and 930 trials in India's own registry (CTRI), asking where India stands as GLP-1 drugs reshape the obesity market.

Data snapshot: 18 November 2026.

**Interactive dashboard:** [India in the Global Obesity Drug Race on Tableau Public](https://public.tableau.com/app/profile/aryan.misra/viz/IndiaintheGlobalObesityDrugRace/IndiaintheGlobalObesityDrugRace)

## Key findings

1. **Industry is taking over obesity research.** Industry sponsored 7 to 11% of new interventional obesity trials each year from 2010 to 2021. In 2025 it was 26%. Interventional trials started per year more than doubled, from 412 (2010) to 897 (2025).
2. **Two companies dominate, and new drug classes are arriving fast.** Novo Nordisk (142 trials since 2018) and Eli Lilly (121) each run 56 Phase 3 obesity trials. GIP/GLP-1 dual agonists such as tirzepatide went from 0 trials before 2018 to 135 since 2022. Oral small-molecule GLP-1 pills went from 0 to 45.
3. **China builds its own pipeline; India hosts other companies' trials.** Since 2018, 257 industry obesity drug trials had Chinese sites, and 207 of them ran only in China. India had 46, of which 2 ran only in India and 41 were Phase 3 trials of multinational drugs. Six of the 15 most active industry sponsors are Chinese companies.
4. **India's home-grown drug activity is invisible to global trackers.** After semaglutide's Indian patent expired in March 2026, seven Indian companies (Alkem, Emcure, Hetero, Macleods, Natco, Sun Pharma, Zydus) registered Phase 3 semaglutide trials in CTRI in 2025 and 2026. All are India-only, and none appear in ClinicalTrials.gov's obesity records.
5. **Most obesity research registered in India is not drug research.** Of 796 interventional obesity trials in CTRI, 54% test traditional medicine (Ayurveda, Unani, Homoeopathy, Siddha) and 13% test yoga or exercise. Only 3% test classified anti-obesity drugs.
6. **Results reporting is weak.** Only 31% of completed industry trials and 18% of non-industry trials on ClinicalTrials.gov posted results.

## Business questions and where they are answered

| # | Question | Query |
| --- | --- | --- |
| 1 | Is obesity research growing? | `q01_trials_per_year` |
| 2 | Drug vs non-drug share | `q02_drug_vs_nondrug_share` |
| 3 | Which drug classes, and how has the mix shifted? | `q03_drug_class_by_period` |
| 4 | Which companies invest most? | `q04_top_industry_sponsors` |
| 5 | Is industry taking over from academia? | `q05_industry_share_by_year` |
| 6 | How mature is the pipeline? | `q06_phase_mix_drug_trials` |
| 7 | Which countries host most trial sites? | `q07_top_countries_by_sites` |
| 8 | Which obesity drug trials run in India, and who sponsors them? | `q08_india_trials` |
| 9 | How often do trials finish vs get terminated? | `q09_completion_vs_failure` |
| 10 | What share of completed trials post results? | `q10_results_reporting` |
| 11 | What does India's own obesity research test? | `q11_ctri_modality_mix` |
| 12 | Who sponsors trials in CTRI? | `q12_ctri_who_sponsors` |
| 13 | Every incretin / anti-obesity drug trial in CTRI | `q13_ctri_incretin_trials` |
| 14 | Is India's own obesity research growing? | `q14_ctri_trend_by_year` |
| 15 | Home-grown vs imported trials: India, China, US, Japan, Korea, Brazil | `q15_india_vs_china_innovation` |

## Data

| Source | What | How it was collected |
| --- | --- | --- |
| [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) | 15,801 studies, condition "obesity OR overweight" | `src/01_download.py` |
| [CTRI](https://ctri.nic.in), via the [WHO ICTRP](https://trialsearch.who.int) mirror | 930 CTRI trials with condition "obesity OR overweight" and recruitment in India | ICTRP result and detail pages (CTRI's own search requires a CAPTCHA). No investigator contact details were stored. |

## Approach

| Step | Script | What it does |
| --- | --- | --- |
| 1 | `src/01_download.py` | Downloads all matching ClinicalTrials.gov studies (paged, 1,000 per request) |
| 2 | `src/02_build_db.py` | Flattens the nested JSON into 4 SQLite tables and tags each trial with a drug class |
| 3 | `src/04_india_registry.py` | Adds the CTRI trials as a 5th table, classified with the same drug rules |
| 4 | `sql/analysis.sql` | 15 SQL queries, one per business question |
| 5 | `src/03_run_analysis.py` | Runs the queries and saves each result to `outputs/` |
| 6 | `src/05_tableau_data.py` | Combines the five dashboard charts into one long-format file, `data/tableau/dashboard_data.csv`, for Tableau Public |

**Drug classification.** Drugs are matched by name, brand name and confirmed company code (for example tirzepatide = LY3298176). New compounds are also matched by their official naming stem: "-glipron" (oral small-molecule GLP-1), "-dutide" (GLP-1/glucagon), "-lintide" (amylin) and "-glutide" (GLP-1 analogue, excluding GLP-2 drugs).

## How to run

```bash
pip install -r requirements.txt
python src/01_download.py
python src/02_build_db.py
python src/04_india_registry.py   # uses data/raw/ictrp_india_details.json.gz (included)
python src/03_run_analysis.py
python src/05_tableau_data.py     # builds the Tableau dashboard input
```

## Limitations

- Trial counts measure activity, not spending or success.
- "Industry" uses ClinicalTrials.gov's sponsor class; CTRI sponsor type is inferred from the sponsor's name.
- Compounds known only by a code not in the rules land in "Other or unclassified drug" (56% of industry drug trials since 2022, many from Chinese developers).
- CTRI records rarely list their ClinicalTrials.gov ID, so overlap between the two registries was checked by sponsor name, not by ID.
- Start years of 2026 and later include planned trials.
