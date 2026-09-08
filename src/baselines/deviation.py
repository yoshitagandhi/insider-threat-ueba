import numpy as np
import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS


def add_deviation_features(daily: pd.DataFrame) -> pd.DataFrame:
    daily = daily.copy()

    for col in FEATURE_COLS:
        mean_col = f"{col}_baseline_mean"
        std_col = f"{col}_baseline_std"
        dev_col = f"{col}_zscore"

        std_safe = daily[std_col].replace(0, np.nan)

        daily[dev_col] = (
            daily[col] - daily[mean_col]
        ) / std_safe

        daily[dev_col] = daily[dev_col].fillna(0)

    return daily


def statistical_anomaly_score(daily: pd.DataFrame) -> pd.Series:
    zscore_cols = [
        f"{c}_zscore"
        for c in FEATURE_COLS
    ]

    return daily[zscore_cols].abs().max(axis=1)