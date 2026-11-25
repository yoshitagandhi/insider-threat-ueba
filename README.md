# Insider Threat Detection via UEBA

An interpretable User and Entity Behavior Analytics (UEBA) project for the CERT
Insider Threat Test Dataset r4.2. Rather than comparing people to a population
average, it asks whether a user's behavior is unusual **for that user**.

The project is deliberately analyst-assistive: an anomaly is an investigation
lead, not evidence of intent and never an automated personnel decision.

## Why this project is interesting

- Builds daily behavior features from logon, device, file, and email events.
- Uses leakage-safe 14-day personal baselines: each day's baseline only sees
  earlier days (`shift(1)` before rolling aggregation).
- Compares an interpretable max-absolute-z-score baseline with Isolation Forest.
- Uses a time-based train/test split: Isolation Forest is fitted on the earlier
  60% of dates and judged on the later 40% it has never seen. The alert
  threshold is taken from the training period only.
- Explains every scored day with a plain-English `top_reasons` column, for
  example `USB activity (+4.2σ), Distinct PCs used (+3.0σ)`.
- Evaluates with precision, recall, F1, PR-AUC, scenario breakdowns, a PR curve,
  confusion matrix, and threshold-sensitivity analysis.
- Measures detection per *insider* as well as per day: an analyst only needs
  one good alert to open a case.
- Adds a 7-day user risk score (rolling average of each user's anomaly score)
  so the analyst queue ranks people, not isolated days.
- Includes an alert-budget analysis (insiders caught vs alerts per day) and a
  feature-group ablation study, both with charts in `reports/`.

## Headline result

> These are the **v2** results (26 Nov 2026). v3 adds three r4.2-1 features
> (after-hours USB, after-hours file activity, first-ever USB use) and the 7-day
> user risk score. Re-run `python -m src.pipeline`,
> `python -m src.evaluation.report` and `python -m src.evaluation.analysis`
> to produce the v3 numbers.

Isolation Forest is fitted on the days before **29 Oct 2010** and evaluated
on the later, unseen days (122,217 user-days, 415 of them malicious). The
alert threshold is the 99th percentile of *training* scores (0.0823).

| Test period | Precision | Recall | F1 | PR-AUC | Alerts |
|---|---|---|---|---|---|
| **Isolation Forest** | **0.028** | **0.070** | **0.040** | **0.015** | 1,025 |
| Max-\|z\| baseline | 0.007 | 0.022 | 0.011 | 0.007 | 1,213 |
| Random guessing | 0.0034 | - | - | 0.0034 | - |

- Only 0.34% of test user-days are malicious, so random alerting would reach a
  precision of about 0.0034. Isolation Forest is **about 8× better than
  random**, and about 3.8× (precision) and 3.2× (recall) better than the
  statistical baseline.
- The training threshold flagged 0.84% of test days, close to the intended 1%,
  so behaviour did not drift much between the two periods.
- That is about 8 alerts a day for the whole organisation, 29 of which were
  true malicious days.

Recall per CERT scenario (test period):

| Scenario | Malicious days | Caught | Recall |
|---|---|---|---|
| r4.2-1 | 28 | 2 | 0.071 |
| r4.2-2 | 375 | 25 | 0.067 |
| r4.2-3 | 12 | 2 | 0.167 |

Day-level recall is low, but an analyst does not need to flag every malicious
day, only one per insider. Counted per person, the model catches **18 of 34
insiders (53%)** in the test period:

| Scenario | Insiders | Caught (≥ 1 alert on a malicious day) | Share |
|---|---|---|---|
| r4.2-1 | 13 | 2 | 15% |
| r4.2-2 | 16 | 14 | **88%** |
| r4.2-3 | 5 | 2 | 40% |
| **All** | **34** | **18** | **53%** |

This changes the reading of the results. r4.2-2 looked like the weakest
scenario per day (6.7% recall) only because those insiders are active for
many days; 14 of the 16 still received at least one alert. The real gap is
**r4.2-1**: short bursts of after-hours logins and first-time USB use just
before the insider leaves. The v3 features target exactly this. r4.2-3 has
only 5 insiders, too few to draw conclusions from.

These numbers are an improvement over the previous version (precision 0.018,
recall 0.062, F1 0.028, PR-AUC 0.014), even though that version was scored on
the same days it was trained on and used a more generous PR-AUC formula. The
absolute numbers are still low: about 97% of alerts are false positives. This
is an early-stage, analyst-assistive detector, not a production-ready one.
`n_estimators=200` and `contamination="auto"` are reasonable defaults and have
not been tuned.

## Architecture

```text
CERT event CSVs
  → per-user/day features
  → 14-day historical personal baseline
  → z-score deviation features (cold-start days left unscored)
  → time-based split: fit on earlier dates, score later dates
  → Isolation Forest anomaly score + top_reasons explanation
  → 7-day user risk score (rolling average per user)
  → CERT answer-file labels for offline evaluation
  → Streamlit analyst dashboard
```

`is_malicious` is strictly evaluation-only. Both Isolation Forest and the
experimental autoencoder train without ground-truth label filtering.

## Reproducibility note

Earlier versions counted Logoff events as logins, filled cold-start z-scores
with 0, and scored the same period they were trained on. All three were
corrected before the results above were produced. Re-running
`python -m src.pipeline` and `python -m src.evaluation.report` on the CERT
r4.2 data reproduces them (`RANDOM_SEED = 42`).

## Dataset and data policy

Source: [CERT Insider Threat Test Dataset, release r4.2](https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247).

Raw events, derived parquet files, and answer files are ignored by Git. Download
the dataset and answer files directly from the source, then place them here:

```text
data/raw/r4.2/
  logon.csv
  device.csv
  file.csv
  email.csv
data/answers/r4.2/
  r4.2-1/ ...
  r4.2-2/ ...
  r4.2-3/ ...
```

The repository's MIT license applies to this project's code, not to CERT data
or answer files; follow the dataset provider's terms for those materials.

## Quick start

Requires Python 3.10+ (tested locally with Python 3.14).

```bash
python -m venv .venv
.venv\Scripts\activate             # Windows
pip install -r requirements-dev.txt
python -m src.pipeline
python -m src.evaluation.report
python -m src.evaluation.analysis
streamlit run dashboard/app.py
```

`src.evaluation.report` prints test-period precision, recall, F1, PR-AUC and
insiders caught for the daily score, the 7-day user risk and the statistical
baseline, broken down by CERT scenario.

`src.evaluation.analysis` writes four files to `reports/`:

- `alert_budget.csv` / `alert_budget.png`: insiders caught and precision at
  six thresholds, shown as alerts per day so a security team can pick a
  threshold from its review capacity.
- `ablation.csv` / `ablation.png`: the model refitted without each feature
  group (logon, USB/device, file, email, and the newest features), showing
  which groups really help. It refits the model six times, so allow a minute.

The pipeline reads multi-gigabyte event data and is I/O and hardware dependent;
allow time accordingly. It writes `data/processed/scored_daily.parquet` and an
ignored `models/isolation_forest.joblib` artifact; the dashboard reads the
scored parquet without refitting a model.

For the optional PyTorch experiment:

```bash
pip install -r requirements-experiments.txt
```

## Evaluation notebook

Open `notebooks/01_eda.ipynb` after generating the scored parquet file. It
includes the class-balance view, PR comparison, threshold-sensitivity table,
confusion matrix, scenario catch-rate visual, and the r4.2-2 score-overlap
analysis that supports the documented limitation.

The 99th-percentile threshold is an operating-point example, not a universal
production setting. The notebook exposes 95th, 97th, 99th, and 99.5th
percentiles so reviewers can inspect the precision/recall trade-off. In a
deployed system, select the threshold from analyst-review capacity and a
time-based validation policy—not from contemporaneous labels.

## Project structure

```text
src/
  data/loaders.py              # raw event loading
  features/user_day.py         # daily behavior features
  baselines/                   # personal and anchored baselines
  models/                      # Isolation Forest and optional autoencoder
  evaluation/                  # labels, metrics, charts, error analysis
  evaluation/report.py         # test-period evaluation report
  evaluation/analysis.py       # alert-budget and ablation charts
  models/user_risk.py          # 7-day user risk score
reports/                       # charts and tables written by analysis.py
dashboard/app.py               # cached Streamlit risk triage view
notebooks/01_eda.ipynb         # EDA and corrected benchmark workflow
tests/                         # unit and evaluation smoke tests
.github/workflows/tests.yml    # Python 3.10–3.12 CI
```

## Testing

```bash
pytest
```

The test suite covers feature correctness (including exclusion of logoff
events and the distinct-PC count), leakage/cold-start behavior, zero-variance
deviations, the standard-deviation floor, `top_reasons` wording, the time-based
split, train-only thresholds, after-hours USB/file counts, the first-ever USB
flag, the backward-looking user risk, feature-group coverage, fixed anchor
baselines, and
evaluation/error-categorization smoke cases. GitHub Actions runs
the suite on Python 3.10, 3.11, and 3.12 for pushes and pull requests.

## Design decisions and limitations

- `http.csv` is intentionally excluded from the production pipeline after an
  experiment found no measured benefit for the difficult r4.2-2 scenario. Its
  chunked feature implementation remains available for follow-up experiments.
- A fixed 21-observation anchor baseline is available as an experiment. Its
  calibration period is unscored and later baselines are frozen, so it cannot
  absorb later behavior.
- Cold-start users remain unscored until three historical days exist; the system
  does not fabricate a population baseline for them. (An earlier version filled
  their z-scores with 0, which silently scored them as perfectly normal. That
  has been fixed: their z-scores now stay empty and the rows are skipped.)
- Each feature's standard deviation is raised to a small floor (1 event, or 0.1
  for the external-recipient ratio) before computing z-scores. Without it, a
  user who had never used a USB drive (std = 0) got a z-score of 0 on the day
  they first plugged one in, which hid exactly the behaviour we want to see.
- Two features were added: `distinct_pcs` (number of different machines logged
  into that day) and `first_logon_hour`. On days with no logon, the first logon
  hour is carried forward from the user's previous day rather than set to 0,
  which would look like a midnight login.
- Three features target CERT scenario r4.2-1: `after_hours_usb_count` (USB
  connections before 06:00 or after 20:00), `after_hours_file_count`, and
  `first_usb_ever`. The last is a 0/1 flag for the first day a user ever
  connects a USB drive, built from a cumulative sum of earlier days only. A
  z-score cannot express "never done before" well (the baseline is flat), so
  the flag goes into the model directly instead of as a z-score.
- `user_risk_7d` is the mean daily anomaly score over the user's last 7 scored
  days, including today and nothing later. It rewards persistence (helpful for
  low-and-slow r4.2-2) but smooths out single-day spikes (less helpful for
  short r4.2-1 bursts). That is why the report shows both scores side by side
  rather than replacing one with the other.
- Isolation Forest is fitted on the first 60% of dates and evaluated on the last
  40%. The alert threshold is the 99th percentile of *training* scores. The
  training period still contains some malicious days; that is acceptable for an
  unsupervised model because labels are never used for fitting.
- Feature-level behavioral anomaly scores do not establish malicious intent.

## Possible next steps

- Try a rolling (walk-forward) split, refitting every month, instead of one
  fixed cut-off date.
- Run a hyperparameter search over Isolation Forest's `n_estimators` and
  `contamination`, which are currently reasonable defaults rather than tuned
  values.
- If r4.2-1 is still weak after v3, add HTTP features for a short list of
  domains (for example file-sharing and job sites). r4.2-1 insiders upload data
  to a leak site, which only `http.csv` can see.
- Combine the daily and 7-day scores (for example, alert if either one crosses
  its threshold) and compare insiders caught at the same alert budget.

## Interview talking points

The strongest engineering decision is the leakage guard: the baseline for day
*t* only contains behavior observed before day *t*. Every later feature (the
carried-forward logon hour, the first-ever USB flag, the 7-day risk) follows
the same rule of looking only backwards.

The most useful analytical lesson is about choosing the right metric. Per day,
r4.2-2 looked like the hardest scenario (6.7% recall). Per insider, 14 of 16
were caught, and the real weakness turned out to be r4.2-1. Measuring the way
an analyst actually works changed which problem was worth solving next.

A second talking point is evaluation honesty: moving from scoring the training
period to a forward-looking time split, and fixing two silent z-score bugs
(cold-start rows and zero-variance users), made the evaluation stricter *and*
improved every Isolation Forest metric.
