"""Choose the Isolation Forest inputs fairly, without looking at the test period.

The training period is split again by date:

    |------------- train (first 60% of dates) -------------|---- test ----|
    |------ fit (first 75% of train) ------|-- validation --|

Each candidate feature set is fitted on "fit" and judged on "validation".
The winner is then refitted on the whole training period and evaluated on
the test period exactly once. Labels are used here only to compare
candidates, never to fit the model itself.
"""

import json
from pathlib import Path

import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS
from src.evaluation.evaluate import evaluate_scores
from src.evaluation.report import insiders_caught, train_threshold
from src.models.isolation_forest_model import fit_isolation_forest, score_isolation_forest, split_by_date
from src.utils.config import ALERT_PERCENTILE

FIT_FRACTION = 0.75
DEFAULT_SET = "v3: all 13 features"

V1_FEATURES = [
    "logon_count", "after_hours_logon_count", "usb_connect_count", "device_event_count",
    "file_event_count", "unique_filenames", "email_count", "total_attachments",
    "external_recipient_ratio",
]
V2_FEATURES = V1_FEATURES + ["first_logon_hour", "distinct_pcs"]
LOGON_GROUP = ["logon_count", "after_hours_logon_count", "first_logon_hour", "distinct_pcs"]
EMAIL_GROUP = ["email_count", "total_attachments", "external_recipient_ratio"]

CANDIDATE_FEATURE_SETS = {
    "v1: original 9 features": V1_FEATURES,
    "v2: + first logon hour, distinct PCs": V2_FEATURES,
    "v3: all 13 features": FEATURE_COLS,
    "v3 without logon group": [f for f in FEATURE_COLS if f not in LOGON_GROUP],
    "v3 without email group": [f for f in FEATURE_COLS if f not in EMAIL_GROUP],
}


def to_columns(features: list[str]) -> list[str]:
    return [f"{feature}_zscore" for feature in features]


def evaluate_candidates(train: pd.DataFrame, fit_fraction: float = FIT_FRACTION) -> pd.DataFrame:
    """Fit every candidate on the fit window and score it on the validation window."""
    fit, validation, cutoff = split_by_date(train, fit_fraction)
    print(f"Feature selection: fit on days before {cutoff}, validate on the rest of the training period")

    rows = []
    for name, features in CANDIDATE_FEATURE_SETS.items():
        columns = to_columns(features)
        model = fit_isolation_forest(fit, columns=columns)

        scored = score_isolation_forest(model, pd.concat([fit, validation]), columns=columns)
        scored["split"] = (scored["day"] < cutoff).map({True: "train", False: "test"})

        val = scored[scored["split"] == "test"]
        threshold = train_threshold(scored, "if_anomaly_score", ALERT_PERCENTILE)
        metrics = evaluate_scores(val, "if_anomaly_score", threshold)
        people = insiders_caught(scored, "if_anomaly_score", ALERT_PERCENTILE).iloc[-1]

        rows.append({
            "candidate": name,
            "n_features": len(features),
            "val_insiders_caught": int(people["caught"]),
            "val_insiders": int(people["insiders"]),
            "val_pr_auc": metrics["pr_auc"],
            "val_precision": metrics["precision"],
        })
    return pd.DataFrame(rows)


def choose_best(table: pd.DataFrame) -> str:
    """Most insiders caught on validation; PR-AUC breaks ties."""
    if table["val_insiders"].max() == 0:
        print("No malicious days in the validation window, keeping the default feature set")
        return DEFAULT_SET
    ranked = table.sort_values(["val_insiders_caught", "val_pr_auc"], ascending=False)
    return ranked.iloc[0]["candidate"]


def select_features(train: pd.DataFrame) -> tuple[str, list[str], pd.DataFrame]:
    table = evaluate_candidates(train)
    best = choose_best(table)
    return best, to_columns(CANDIDATE_FEATURE_SETS[best]), table


def save_selection(name: str, columns: list[str], table: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "selected": name,
        "columns": columns,
        "validation_results": table.to_dict(orient="records"),
    }
    path.write_text(json.dumps(record, indent=2, default=float))


def load_selected_columns(path: Path) -> list[str] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())["columns"]
