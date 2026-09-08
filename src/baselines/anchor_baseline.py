import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS


def add_anchor_baseline(
    daily: pd.DataFrame,
    anchor_days: int = 21,
    min_periods: int = 3,
) -> pd.DataFrame:
    """Add a fixed baseline learned from each user's initial anchor period.

    The first ``anchor_days`` observations are calibration-only. Later rows use
    that same frozen baseline, so it cannot absorb later attack behavior.
    """
    if anchor_days < min_periods:
        raise ValueError("anchor_days must be at least min_periods")

    daily = daily.copy()
    daily = daily.sort_values(["user", "day"])

    def add_user_anchor(user_days: pd.DataFrame) -> pd.DataFrame:
        anchored = user_days.copy()
        calibration = anchored.iloc[:anchor_days]
        eligible = anchored.index[anchor_days:]
        for col in FEATURE_COLS:
            anchored[f"{col}_anchor_mean"] = pd.NA
            anchored[f"{col}_anchor_std"] = pd.NA
            if len(calibration) >= min_periods:
                anchored.loc[eligible, f"{col}_anchor_mean"] = calibration[col].mean()
                anchored.loc[eligible, f"{col}_anchor_std"] = calibration[col].std()
        return anchored

    anchored_groups = [
        add_user_anchor(user_days)
        for _, user_days in daily.groupby("user", sort=False)
    ]
    daily = pd.concat(anchored_groups).sort_index()

    return daily
