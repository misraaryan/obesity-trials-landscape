-- Obesity clinical trial landscape: business questions
-- Database: data/processed/obesity_trials.db
-- Each query starts with a "-- name:" line so 03_run_analysis.py can run and save it.
-- Scope for most questions: INTERVENTIONAL trials starting 2010 or later.


-- name: q01_trials_per_year
-- Q1. Is research activity in obesity growing? Interventional trials started per year.
SELECT start_year,
       COUNT(*) AS trials
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year BETWEEN 2010 AND 2026
GROUP BY start_year
ORDER BY start_year;


-- name: q02_drug_vs_nondrug_share
-- Q2. How much of obesity research tests drugs vs lifestyle, devices, surgery?
SELECT CASE
         WHEN drug_class LIKE 'Non-drug%' OR drug_class = 'No intervention listed' THEN 'Non-drug'
         ELSE 'Drug'
       END AS category,
       COUNT(*) AS trials,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year >= 2010
GROUP BY category;


-- name: q03_drug_class_by_period
-- Q3. Which drug classes are being tested, and how has the mix shifted?
SELECT drug_class,
       SUM(CASE WHEN start_year BETWEEN 2010 AND 2017 THEN 1 ELSE 0 END) AS trials_2010_2017,
       SUM(CASE WHEN start_year BETWEEN 2018 AND 2021 THEN 1 ELSE 0 END) AS trials_2018_2021,
       SUM(CASE WHEN start_year >= 2022 THEN 1 ELSE 0 END)               AS trials_2022_on,
       COUNT(*) AS total
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year >= 2010
  AND drug_class NOT LIKE 'Non-drug%'
  AND drug_class NOT IN ('Other or unclassified drug', 'No intervention listed')
GROUP BY drug_class
ORDER BY total DESC;


-- name: q04_top_industry_sponsors
-- Q4. Who is investing? Top 15 industry sponsors of obesity drug trials since 2018.
SELECT lead_sponsor,
       COUNT(*) AS trials,
       SUM(CASE WHEN phase LIKE '%PHASE3%' THEN 1 ELSE 0 END) AS phase3_trials
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND sponsor_class = 'INDUSTRY'
  AND start_year >= 2018
GROUP BY lead_sponsor
ORDER BY trials DESC
LIMIT 15;


-- name: q05_industry_share_by_year
-- Q5. Is industry taking over obesity research from academia?
SELECT start_year,
       COUNT(*) AS trials,
       ROUND(100.0 * SUM(CASE WHEN sponsor_class = 'INDUSTRY' THEN 1 ELSE 0 END) / COUNT(*), 1) AS industry_pct
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year BETWEEN 2010 AND 2026
GROUP BY start_year
ORDER BY start_year;


-- name: q06_phase_mix_drug_trials
-- Q6. How mature is the drug pipeline? Phase mix of drug trials since 2018.
SELECT phase,
       COUNT(*) AS trials,
       ROUND(AVG(enrollment), 0) AS avg_enrollment
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year >= 2018
  AND drug_class NOT LIKE 'Non-drug%'
  AND drug_class <> 'No intervention listed'
GROUP BY phase
ORDER BY trials DESC;


-- name: q07_top_countries_by_sites
-- Q7. Where are trials run? Top 20 countries by number of trial sites (drug trials since 2018).
SELECT l.country,
       COUNT(*)                 AS sites,
       COUNT(DISTINCT l.nct_id) AS trials
FROM locations l
JOIN trials t ON t.nct_id = l.nct_id
WHERE t.study_type = 'INTERVENTIONAL'
  AND t.start_year >= 2018
  AND t.drug_class NOT LIKE 'Non-drug%'
  AND l.country IS NOT NULL
GROUP BY l.country
ORDER BY sites DESC
LIMIT 20;


-- name: q08_india_trials
-- Q8. India specifically: which obesity drug trials have Indian sites, and who runs them?
SELECT t.lead_sponsor,
       t.drug_class,
       COUNT(DISTINCT t.nct_id) AS trials,
       COUNT(*)                 AS indian_sites
FROM trials t
JOIN locations l ON l.nct_id = t.nct_id
WHERE l.country = 'India'
  AND t.study_type = 'INTERVENTIONAL'
  AND t.start_year >= 2015
GROUP BY t.lead_sponsor, t.drug_class
ORDER BY trials DESC, indian_sites DESC;


-- name: q09_completion_vs_failure
-- Q9. How often do trials finish? Final status of closed trials, industry vs non-industry.
SELECT CASE WHEN sponsor_class = 'INDUSTRY' THEN 'Industry' ELSE 'Non-industry' END AS sponsor_type,
       overall_status,
       COUNT(*) AS trials,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY CASE WHEN sponsor_class = 'INDUSTRY' THEN 'Industry' ELSE 'Non-industry' END), 1) AS pct
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND start_year BETWEEN 2010 AND 2022
  AND overall_status IN ('COMPLETED', 'TERMINATED', 'WITHDRAWN', 'SUSPENDED')
GROUP BY sponsor_type, overall_status
ORDER BY sponsor_type, trials DESC;


-- name: q10_results_reporting
-- Q10. Transparency: what share of completed trials posted results on ClinicalTrials.gov?
SELECT CASE WHEN sponsor_class = 'INDUSTRY' THEN 'Industry' ELSE 'Non-industry' END AS sponsor_type,
       COUNT(*) AS completed_trials,
       ROUND(100.0 * SUM(has_results) / COUNT(*), 1) AS pct_with_results
FROM trials
WHERE study_type = 'INTERVENTIONAL'
  AND overall_status = 'COMPLETED'
  AND start_year BETWEEN 2010 AND 2022
GROUP BY sponsor_type;


-- ===========================================================================
-- India deep-dive: CTRI (India's own registry), table ctri_trials
-- ===========================================================================

-- name: q11_ctri_modality_mix
-- Q11. What does obesity research registered in India actually test?
SELECT modality,
       COUNT(*) AS trials,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM ctri_trials
WHERE study_type = 'Interventional'
GROUP BY modality
ORDER BY trials DESC;


-- name: q12_ctri_who_sponsors
-- Q12. Who sponsors Indian obesity trials, and what kind?
SELECT sponsor_type,
       modality,
       COUNT(*) AS trials
FROM ctri_trials
WHERE study_type = 'Interventional'
GROUP BY sponsor_type, modality
ORDER BY sponsor_type, trials DESC;


-- name: q13_ctri_incretin_trials
-- Q13. Every incretin / anti-obesity drug trial registered in India: global or home-grown?
SELECT registration_year,
       sponsor,
       sponsor_type,
       drug_class,
       phase,
       india_only,
       also_on_ctgov,
       title
FROM ctri_trials
WHERE drug_class IS NOT NULL
ORDER BY registration_year DESC, sponsor;


-- name: q14_ctri_trend_by_year
-- Q14. Is India's own obesity research growing, and is industry part of it?
SELECT registration_year,
       COUNT(*) AS trials,
       SUM(CASE WHEN sponsor_type <> 'Academic / hospital / government' THEN 1 ELSE 0 END) AS industry_trials,
       SUM(CASE WHEN modality = 'Anti-obesity drug (classified)' THEN 1 ELSE 0 END) AS incretin_or_obesity_drug_trials
FROM ctri_trials
WHERE registration_year BETWEEN 2010 AND 2026
GROUP BY registration_year
ORDER BY registration_year;


-- name: q15_india_vs_china_innovation
-- Q15. ClinicalTrials.gov: are a country's industry obesity drug trials home-grown or imported?
-- "Domestic-only" = every site of the trial is in that one country.
WITH t AS (
    SELECT * FROM trials
    WHERE study_type = 'INTERVENTIONAL' AND start_year >= 2018 AND sponsor_class = 'INDUSTRY'
      AND drug_class NOT LIKE 'Non-drug%' AND drug_class <> 'No intervention listed'
),
c AS (SELECT nct_id, COUNT(DISTINCT country) AS n_countries FROM locations GROUP BY nct_id)
SELECT l.country,
       COUNT(DISTINCT t.nct_id) AS industry_drug_trials,
       COUNT(DISTINCT CASE WHEN c.n_countries = 1 THEN t.nct_id END) AS domestic_only,
       COUNT(DISTINCT CASE WHEN t.phase LIKE '%PHASE3%' THEN t.nct_id END) AS phase3
FROM t
JOIN locations l ON l.nct_id = t.nct_id
JOIN c ON c.nct_id = t.nct_id
WHERE l.country IN ('India', 'China', 'United States', 'Japan', 'South Korea', 'Brazil')
GROUP BY l.country
ORDER BY industry_drug_trials DESC;
