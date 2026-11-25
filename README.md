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
- Documents a real limitation: the sustained, low-and-slow r4.2-2 scenario is
  substantially harder to surface than acute behavioral deviations.

## Headline result

> **Re-run needed.** The numbers below were produced *before* the November 2026
> improvements (cold-start fix, standard-deviation floor, two new features,
> time-based split, average-precision PR-AUC). They score the same period the
> model was trained on, so they are not comparable with the new test-period
> results. Run `python -m src.pipeline` and then
> `python -m src.evaluation.report` to get the current figures.

Previous result: at the 99th-percentile alert threshold, Isolation Forest reaches **precision
≈ 0.018, recall ≈ 0.062, F1 ≈ 0.028, PR-AUC ≈ 0.014**, against a statistical
max‑|z| baseline of precision ≈ 0.003 and recall ≈ 0.009. Isolation Forest is
roughly 5–7× better than the statistical baseline on every metric, but the
absolute numbers are still low: at this threshold the model catches about 6%
of true malicious user-days, and roughly 98% of its alerts are false
positives. This is an early-stage detector, not a production-ready one — see
[Design decisions and limitations](#design-decisions-and-limitations) for why,
and [Evaluation notebook](#evaluation-notebook) for the full breakdown.
`n_estimators=200` and `contamination="auto"` were used as reasonable
defaults; hyperparameters have not been tuned via grid or random search.

## Architecture

```text
CERT event CSVs
  → per-user/day features
  → 14-day historical personal baseline
  → z-score deviation features (cold-start days left unscored)
  → time-based split: fit on earlier dates, score later dates
  → Isolation Forest anomaly score + top_reasons explanation
  → CERT answer-file labels for offline evaluation
  → Streamlit analyst dashboard
```

`is_malicious` is strictly evaluation-only. Both Isolation Forest and the
experimental autoencoder train without ground-truth label filtering.

## Reproducibility note

The project previously computed logon features over both `Logon` and `Logoff`
events. That implementation defect has been corrected: login count and login
time features now use only `Logon` events. Consequently, prior published model
metrics are not presented as current results. Re-run the pipeline and notebook
against the downloaded data to produce the reproducible, corrected benchmark.

This is intentional: keeping stale scores would be less credible than making a
methodological correction explicit.

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
streamlit run dashboard/app.py
```

`src.evaluation.report` prints the test-period precision, recall, F1 and PR-AUC
for both models, plus Isolation Forest recall for each CERT scenario.

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
split, train-only thresholds, fixed anchor baselines, and
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
- Explore why the anchor-baseline and HTTP-feature experiments didn't move the
  needle on the r4.2-2 scenario specifically, since that remains the project's
  main open analytical question.

## Interview talking points

The strongest engineering decision is the leakage guard: the baseline for day
*t* only contains behavior observed before day *t*. The most useful analytical
result is negative: r4.2-2's weak, sustained behavior overlaps normal user
variance, and neither a frozen anchor baseline nor HTTP aggregates materially
resolved that limitation. This project shows both what worked and why a tempting
complexity increase was not adopted.
