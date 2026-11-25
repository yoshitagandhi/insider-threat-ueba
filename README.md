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
- Chooses the model's inputs on a validation window cut from the training
  period, so the test period is used exactly once.
- Combines the model with one hand-written rule (first-ever USB use after
  hours), the way real security teams mix rules and machine learning.
- Tests a combined alert queue that merges the daily score and the 7-day risk
  through training percentiles, with no hand-picked weights.
- Measures early warning: insiders alerted in the week *before* their attack,
  checked against a chance level, because day-level labels miss those alerts.
- Adds a 7-day user risk score (each user's highest daily score in the last
  week) so the analyst queue ranks people, not isolated days.
- Includes an alert-budget analysis (insiders caught vs alerts per day) and a
  feature-group ablation study, both with charts in `reports/`.

## Headline result

Results from the v4 pipeline (26 Nov 2026 run). The model is fitted on days
before **29 Oct 2010** and evaluated on the later, unseen days: 122,217
user-days, 415 of them malicious, belonging to 34 insiders. Every threshold is
the 99th percentile of *training* scores, so no test information is used to
set it.

| Test period | Insiders caught | Precision | Recall (days) | F1 | PR-AUC | Alerts per day |
|---|---|---|---|---|---|---|
| **Combined queue: daily OR 7-day risk + rule** | **24/34 (71%)** | **0.041** | **0.106** | **0.059** | 0.034 | 5.3 |
| Hybrid: Isolation Forest + USB rule | 21/34 | 0.030 | 0.072 | 0.043 | 0.024 | 5.0 |
| Isolation Forest (daily) | 20/34 | 0.029 | 0.070 | 0.041 | 0.023 | 5.0 |
| 7-day user risk (max) | 16/34 | 0.038 | 0.094 | 0.054 | **0.035** | 5.2 |
| Max-\|z\| baseline | 8/34 | 0.008 | 0.022 | 0.011 | 0.007 | 5.9 |
| Random guessing | - | 0.0034 | - | - | 0.0034 | - |

- About **5 alerts a day** for the whole organisation (a ~1,000-person
  company), and the combined queue catches **71% of insiders** at that budget.
- Precision is about **12× better than random** (only 0.34% of test days are
  malicious) and 5× better than the statistical baseline.
- The combined queue wins at every alert budget: at about 10 alerts a day it
  catches **29 of 34** insiders, and at about 2.7 a day it still catches 19.

Insiders caught per scenario (at least one alert on a malicious test day):

| Scenario | Insiders | Isolation Forest | Hybrid | 7-day risk (max) | **Combined** | Baseline |
|---|---|---|---|---|---|---|
| r4.2-1 | 13 | 4 | 4 | **11** | **11** | 2 |
| r4.2-2 | 16 | **14** | **14** | 4 | 10 | 6 |
| r4.2-3 | 5 | 2 | **3** | 1 | **3** | 0 |
| **All** | **34** | 20 | 21 | 16 | **24** | 8 |

The daily score and the 7-day risk catch almost opposite scenarios: the daily
score catches the long-running r4.2-2 insiders, and the 7-day max catches the
short r4.2-1 bursts. The combined queue gives each about half of the same
alert budget. It turns each score into a training percentile and takes the
higher one, so no weights are picked by hand.

### Early warning: alerts in the week before the attack

CERT labels only the attack days themselves. An alert a few days *earlier* is
just as useful to an analyst, but day-level labels count it as a false
positive. The report therefore also counts an insider as caught if an alert
came during the attack **or in the 7 days before it**. Every score is measured
the same way, with a chance check: the share of random 8-day windows of normal
(never-malicious) users that contain an alert.

| Test period | During attack | **During or ≤ 7 days before** | Chance level |
|---|---|---|---|
| **Hybrid: Isolation Forest + USB rule** | 21/34 | **30/34 (88%)** | 3.1% |
| Isolation Forest (daily) | 20/34 | 29/34 | 3.1% |
| Combined queue | **24/34** | 26/34 | 2.0% |
| 7-day user risk (max) | 16/34 | 17/34 | 1.1% |
| Max-\|z\| baseline | 8/34 | 14/34 | 5.3% |

- **88% of insiders get an alert during the attack or in the week before it**,
  compared with a 3% chance for a random normal user's week. By chance alone
  you would expect about one of the 34 insiders to be credited.
- **r4.2-1 rises to 13/13** under this view. The rule diagnosis shows why: for
  all 13 r4.2-1 insiders, the first-ever-USB-after-hours rule fired on their
  first USB day, **1 to 13 days before** CERT's first labelled attack day, and
  the daily model also flagged that day. The rule fired on only 36 user-days
  in 17 months.
- **The best model depends on the question.** To catch people *during* the
  attack, the combined queue is best (24/34). To catch them *before or during*
  it, the hybrid is best (30/34). The combined queue gives half its budget to
  the 7-day risk, which carries spikes forward and so adds little early
  warning.

### Progress across versions

| Version | What changed | Insiders caught | Precision | PR-AUC |
|---|---|---|---|---|
| v1 | Scored on the training period itself | (not measured) | 0.018 | 0.014 |
| v2 | Cold-start and zero-variance fixes, time split | 18/34 | 0.028 | 0.015 |
| v3 | Three r4.2-1 features fed into the model | 12/34 | 0.015 | 0.014 |
| v4 hybrid | Validation-selected features + rule | 21/34 | 0.030 | 0.024 |
| **v4 combined** | + daily OR 7-day risk queue | **24/34** | **0.041** | **0.034** |

v1 was scored on the same days it was trained on and used a more generous
PR-AUC formula, so its row is not directly comparable. Most alerts are still
false positives, so this is an analyst-assistive detector, not an automated
one. `n_estimators=200` and `contamination="auto"` have not been tuned.

### Charts

Generated by `python -m src.evaluation.analysis`:

![Insiders caught vs alert budget](reports/alert_budget.png)

![Insiders caught when a feature group is removed](reports/ablation.png)

The ablation uses the test period, so it explains results but is never used to
choose the model.

## What v3 taught us

v3 added three features aimed at r4.2-1 (after-hours USB, after-hours file
activity, and a 0/1 "first-ever USB use" flag fed straight into Isolation
Forest), plus a 7-day *average* risk score.

| Insiders caught (test) | v2 | v3 |
|---|---|---|
| r4.2-1 (the target) | 2/13 | **5/13** |
| r4.2-2 | 14/16 | **4/16** |
| r4.2-3 | 2/5 | 3/5 |
| **All** | **18/34** | **12/34** |
| Precision (daily) | 0.028 | 0.015 |

- The features worked on their target: r4.2-1 more than doubled.
- But the alert budget is fixed (top 1% of days). The new inputs, especially
  the 0/1 flag, made ordinary users' first-USB and after-hours days look
  extreme. Those days took alert slots that used to go to r4.2-2 insiders.
  Isolation Forest also picks features at random, so every weak extra input
  dilutes the strong ones.
- A test-period ablation confirmed it: removing feature groups *helped*.
  The original 9 features alone caught 18/34 with precision 0.026; without the
  logon group, PR-AUC rose to 0.022.
- The 7-day average risk caught only 3/34: averaging smoothed away the
  single-day spikes that actually catch insiders.

The tempting fix, picking the best ablation row, would mean choosing the model
by looking at the test set. v4 does it properly instead:

1. **Validation-based feature selection** (`src/models/feature_selection.py`).
   The training period is split again by date (first 75% fit, last 25%
   validation). Five candidate feature sets (v1, v2, v3, v3 without logon,
   v3 without email) are compared on validation, ranked by insiders caught,
   with PR-AUC as the tie-break. The winner is refitted on the full training
   period and tested once. The choice is saved in
   `models/selected_features.json`.
2. **Hybrid rule** (`src/models/rules.py`). The first-ever-USB flag no longer
   goes into the model. Instead, a rule fires on a user's first-ever USB day
   if they were also active after hours, and `hybrid_score` puts those days
   above every model-only day. The rule fires rarely, so it targets r4.2-1
   without taking alert slots away from r4.2-2.
3. **7-day risk uses the maximum, not the average**, so a strong spike keeps a
   user near the top of the queue for a week.

## Architecture

```text
CERT event CSVs
  → per-user/day features
  → 14-day historical personal baseline
  → z-score deviation features (cold-start days left unscored)
  → time-based split: fit on earlier dates, score later dates
  → feature-set selection on a validation window inside the training period
  → Isolation Forest anomaly score + top_reasons explanation
  → hybrid score: model + first-ever-USB-after-hours rule
  → 7-day user risk score (rolling max per user)
  → combined queue: daily score OR 7-day risk, at the same alert budget
  → CERT answer-file labels for offline evaluation
  → Streamlit analyst dashboard, ranked by the combined risk score, with the
    alert source (rule, today's behaviour, or 7-day carry-over) for each day
```

`is_malicious` is never used to fit a model. It is used for test-period
evaluation and, inside the training period only, to compare candidate feature
sets on the validation window.

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
  group (logon, USB/device, file, email, and the newest features), compared
  with the selected model. It uses the test period, so it explains results but
  is never used to choose the model. It refits the model several times, so
  allow a minute.

The pipeline reads multi-gigabyte event data and is I/O and hardware dependent;
allow time accordingly. It writes `data/processed/scored_daily.parquet` and an
ignored `models/isolation_forest.joblib` artifact; the dashboard reads the
scored parquet without refitting a model.

For the optional PyTorch experiment:

```bash
pip install -r requirements-experiments.txt
```

## Evaluation notebook

Open `notebooks/01_eda.ipynb` after running `python -m src.pipeline`. It walks
through the raw data, features, personal baselines, the validation-based
feature selection, and a test-period evaluation: the report table, insiders
caught per scenario, the r4.2-1 rule diagnosis, class balance, PR curves, the
alert-budget chart, the confusion matrix, a user timeline and error analysis.
All thresholds come from the training period.

The 99th-percentile threshold is an operating-point example, not a universal
production setting. The alert-budget chart shows insiders caught at the 95th
to 99.9th percentiles as alerts per day, so a security team can pick the
threshold from its review capacity rather than from test labels.

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
  models/feature_selection.py  # validation-based choice of model inputs
  models/rules.py              # first-ever-USB-after-hours rule + hybrid score
  models/combined.py           # combined queue from training percentiles
  evaluation/diagnosis.py      # why the rule did or did not catch each insider
reports/                       # charts and tables written by analysis.py
dashboard/app.py               # Streamlit triage view, ranked by combined risk
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
flag, the hybrid rule, the combined queue, the alert source, the rule
diagnosis, the early-warning count,
feature-selection ranking and fallback, the
backward-looking user risk, feature-group coverage, fixed anchor
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
  connects a USB drive, built from a cumulative sum of earlier days only. In v3
  it went into the model directly and crowded out other alerts; in v4 it is
  only used by the hybrid rule.
- `user_risk_7d` is the highest daily anomaly score over the user's last 7
  scored days, including today and nothing later. v3 used the average, which
  smoothed away the spikes that catch insiders.
- The feature-group ablation in `reports/` is computed on the test period, so
  it is a diagnostic that explains results. It is never used to pick the
  model; that happens on the validation window.
- Isolation Forest is fitted on the first 60% of dates and evaluated on the last
  40%. The alert threshold is the 99th percentile of *training* scores. The
  training period still contains some malicious days; that is acceptable for an
  unsupervised model because labels are never used for fitting.
- The early-warning window is a fixed 7 days, chosen before looking at the
  results and not tuned. Its chance check uses normal users only, so the
  comparison is not flattered by other insiders' alerts.
- In the dashboard, a high risk score on a quiet day usually comes from the
  7-day risk carrying an earlier spike forward. The "Alert source" column
  says so explicitly.
- Feature-level behavioral anomaly scores do not establish malicious intent.

## Possible next steps

- Try a rolling (walk-forward) split, refitting every month, instead of one
  fixed cut-off date.
- Run a hyperparameter search over Isolation Forest's `n_estimators` and
  `max_samples` on the same validation window used for feature selection.
- If r4.2-1 is still weak in v4, add HTTP features for a short list of
  domains (for example file-sharing and job sites). r4.2-1 insiders upload data
  to a leak site, which only `http.csv` can see.

## Interview talking points

The strongest engineering decision is the leakage guard: the baseline for day
*t* only contains behavior observed before day *t*. Every later feature (the
carried-forward logon hour, the first-ever USB flag, the 7-day risk) follows
the same rule of looking only backwards.

The most useful analytical lesson is about choosing the right metric. Per day,
r4.2-2 looked like the hardest scenario (6.7% recall). Per insider, 14 of 16
were caught, and the real weakness turned out to be r4.2-1. Measuring the way
an analyst actually works changed which problem was worth solving next. The
same idea led to the early-warning count: the first-ever-USB rule looked
useless on attack-day labels, but it fired days before the attack for every
r4.2-1 insider.

The third lesson is about honest model selection. The v3 features improved
their target scenario but hurt overall, and the best-looking fix came from the
test set. Moving that choice to a validation window inside the training
period, and turning the flag into a rule, keeps the final test result
trustworthy.

A second talking point is evaluation honesty: moving from scoring the training
period to a forward-looking time split, and fixing two silent z-score bugs
(cold-start rows and zero-variance users), made the evaluation stricter *and*
improved every Isolation Forest metric.
