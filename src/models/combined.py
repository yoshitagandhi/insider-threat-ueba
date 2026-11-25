import numpy as np
import pandas as pd

from src.models.rules import RULE_BOOST


def train_percentile(scored: pd.DataFrame, score_col: str) -> np.ndarray:
    """Where each score sits among the TRAINING scores, from 0 (lowest) to 1 (highest).

    Only training scores are used as the reference, so no test information leaks in.
    """
    train_scores = np.sort(scored.loc[scored["split"] == "train", score_col].to_numpy())
    return np.searchsorted(train_scores, scored[score_col].to_numpy(), side="right") / len(train_scores)


def add_combined_score(scored: pd.DataFrame) -> pd.DataFrame:
    """One alert queue fed by both the daily score and the 7-day risk.

    The two scores are on different scales, so each is first turned into a
    training percentile. A day's combined score is the higher of the two, so it
    is flagged if EITHER score is unusual. The rule boost is added on top, the
    same way as in the hybrid score.

    Thresholding combined_score at its own 99th training percentile keeps the
    alert budget at 1% of days, the same as every other score. In practice each
    score gets roughly half of that budget. No weights are chosen by hand.
    """
    scored = scored.copy()
    daily_rank = train_percentile(scored, "if_anomaly_score")
    risk_rank = train_percentile(scored, "user_risk_7d")
    scored["combined_score"] = np.maximum(daily_rank, risk_rank) + RULE_BOOST * scored["rule_alert"]
    return scored


def add_risk_score(scored: pd.DataFrame) -> pd.DataFrame:
    """The single score the dashboard ranks users by.

    It is the combined score capped at 1.0, so it reads as a percentile: 0.995
    means "more unusual than 99.5% of training days". Rule days (which carry
    the +10 boost) show as 1.0. Older files without combined_score fall back
    to the daily Isolation Forest score.
    """
    scored = scored.copy()
    if "combined_score" in scored.columns:
        scored["risk_score"] = scored["combined_score"].clip(upper=1.0)
    else:
        scored["risk_score"] = scored["if_anomaly_score"]
    return scored
