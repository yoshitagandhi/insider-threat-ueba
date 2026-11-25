import pandas as pd

USER_RISK_WINDOW = 7


def add_user_risk(
    scored: pd.DataFrame,
    score_col: str = "if_anomaly_score",
    window: int = USER_RISK_WINDOW,
) -> pd.DataFrame:
    """Add user_risk_7d: the user's highest anomaly score over their last 7 scored days.

    An earlier version used the 7-day average, but averaging smoothed away
    the single-day spikes that actually catch insiders (3 of 34 caught versus
    12 for the daily score). The maximum keeps a strong spike visible for a
    week, so a user stays near the top of the analyst queue until reviewed.
    The window only covers today and earlier days, so it never uses future
    behaviour.
    """
    scored = scored.sort_values(["user", "day"]).copy()
    scored["user_risk_7d"] = scored.groupby("user")[score_col].transform(
        lambda scores: scores.rolling(window, min_periods=1).max()
    )
    return scored


def top_risk_users(scored: pd.DataFrame, day, n: int = 10) -> pd.DataFrame:
    """The n users with the highest 7-day risk on a given day, for an analyst's daily queue."""
    today = scored[scored["day"] == day]
    columns = ["user", "user_risk_7d", "if_anomaly_score"]
    if "top_reasons" in today.columns:
        columns.append("top_reasons")
    return today.nlargest(n, "user_risk_7d")[columns].reset_index(drop=True)
