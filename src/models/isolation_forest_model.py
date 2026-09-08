from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest

from src.baselines.personal_baseline import FEATURE_COLS
from src.utils.config import RANDOM_SEED

ZSCORE_COLS = [f"{c}_zscore" for c in FEATURE_COLS]


def fit_isolation_forest(daily, contamination: float = "auto") -> IsolationForest:
    train_ready = daily.dropna(subset=ZSCORE_COLS)
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=RANDOM_SEED,
    )
    model.fit(train_ready[ZSCORE_COLS])
    return model


def score_isolation_forest(model: IsolationForest, daily):
    train_ready = daily.dropna(subset=ZSCORE_COLS).copy()
    # decision_function: higher = more normal, so we flip sign for "higher = more anomalous"
    train_ready["if_anomaly_score"] = -model.decision_function(train_ready[ZSCORE_COLS])
    return train_ready


def save_isolation_forest(model: IsolationForest, path: Path) -> None:
    """Persist a fitted model for reproducibility or later batch scoring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
