import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS, FEATURE_LABELS, NOVELTY_LABELS

DEFAULT_STD_FLOOR = 1.0
STD_FLOOR = {
    "external_recipient_ratio": 0.1,
}


def add_deviation_features(daily: pd.DataFrame) -> pd.DataFrame:
    """Add one z-score column per feature: how unusual today is for this user.

    Two rules keep the z-scores honest:

    1. Cold start: if a user has no baseline yet (fewer than 3 earlier days),
       the z-score stays empty (NaN). Those days are not scored at all instead
       of pretending they are perfectly normal.
    2. Small spread: if a user's history barely varies (for example they have
       never used a USB drive, so std = 0), dividing by that std would give
       0 or infinity. The std is raised to a minimum "floor" first, so a first
       ever USB connection shows up as a clear positive deviation.
    """
    daily = daily.copy()

    for col in FEATURE_COLS:
        mean = daily[f"{col}_baseline_mean"]
        std = daily[f"{col}_baseline_std"]
        floor = STD_FLOOR.get(col, DEFAULT_STD_FLOOR)

        std_safe = std.clip(lower=floor)
        daily[f"{col}_zscore"] = (daily[col] - mean) / std_safe

    return daily


def statistical_anomaly_score(daily: pd.DataFrame) -> pd.Series:
    """Largest absolute z-score of the day. NaN for cold-start days."""
    zscore_cols = [f"{c}_zscore" for c in FEATURE_COLS]
    return daily[zscore_cols].abs().max(axis=1, skipna=False)


def top_reasons(row: pd.Series, n: int = 3) -> str:
    """Turn the biggest z-scores of one day into a short, readable explanation.

    Example output: "First-ever USB use, USB activity (+4.2σ), File activity (+3.1σ)"
    Novelty flags, when present and switched on, are always listed first.
    """
    parts = []
    if row.get("rule_alert", 0) == 1:
        parts.append("Rule: first-ever USB use after hours")
    else:
        for col, label in NOVELTY_LABELS.items():
            if row.get(col, 0) == 1:
                parts.append(label)

    zscores = {}
    for col in FEATURE_COLS:
        value = row[f"{col}_zscore"]
        if pd.notna(value):
            zscores[col] = value

    biggest = sorted(zscores, key=lambda col: abs(zscores[col]), reverse=True)[:n]

    for col in biggest:
        parts.append(f"{FEATURE_LABELS[col]} ({zscores[col]:+.1f}σ)")
    return ", ".join(parts)


def add_top_reasons(daily: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    daily = daily.copy()
    daily["top_reasons"] = daily.apply(top_reasons, axis=1, n=n)
    return daily
