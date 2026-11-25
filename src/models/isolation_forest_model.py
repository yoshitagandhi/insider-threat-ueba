from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.baselines.personal_baseline import FEATURE_COLS
from src.utils.config import RANDOM_SEED, TRAIN_FRACTION

ZSCORE_COLS = [f"{c}_zscore" for c in FEATURE_COLS]


def split_by_date(daily: pd.DataFrame, train_fraction: float = TRAIN_FRACTION):
    """Split rows by calendar date: earlier days are "train", later days are "test".

    The model only learns from the train period and is then judged on days it
    has never seen, which is how it would be used in real life.
    """
    days = sorted(daily["day"].unique())
    cutoff = days[int(len(days) * train_fraction)]
    train = daily[daily["day"] < cutoff]
    test = daily[daily["day"] >= cutoff]
    return train, test, cutoff


def fit_isolation_forest(daily: pd.DataFrame, contamination: float | str = "auto") -> IsolationForest:
    """Fit on score-ready rows only. Cold-start rows (NaN z-scores) are skipped."""
    train_ready = daily.dropna(subset=ZSCORE_COLS)
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=RANDOM_SEED,
    )
    model.fit(train_ready[ZSCORE_COLS])
    return model


def score_isolation_forest(model: IsolationForest, daily: pd.DataFrame) -> pd.DataFrame:
    """Score every row that has a baseline.

    sklearn's decision_function is higher for normal rows, so the sign is
    flipped: in if_anomaly_score, higher always means more unusual.
    """
    scored = daily.dropna(subset=ZSCORE_COLS).copy()
    scored["if_anomaly_score"] = -model.decision_function(scored[ZSCORE_COLS])
    return scored


def save_isolation_forest(model: IsolationForest, path: Path) -> None:
    """Persist a fitted model for reproducibility or later batch scoring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
