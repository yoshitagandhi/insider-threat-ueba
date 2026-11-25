import pandas as pd

USER_RISK_WINDOW = 7


def add_user_risk(
    scored: pd.DataFrame,
    score_col: str = "if_anomaly_score",
    window: int = USER_RISK_WINDOW,
) -> pd.DataFrame:
    """Add user_risk_7d: the average anomaly score of the user's last 7 scored days.

    A single odd day is often noise, but a user who stays a little unusual for a
    whole week is worth a look. This is exactly the "low-and-slow" pattern of
    CERT scenario r4.2-2. The window only covers today and earlier days, so it
    never uses future behaviour.
    """
    scored = scored.sort_values(["user", "day"]).copy()
    scored["user_risk_7d"] = scored.groupby("user")[score_col].transform(
        lambda scores: scores.rolling(window, min_periods=1).mean()
    )
    return scored


def top_risk_users(scored: pd.DataFrame, day, n: int = 10) -> pd.DataFrame:
    """The n users with the highest 7-day risk on a given day, for an analyst's daily queue."""
    today = scored[scored["day"] == day]
    columns = ["user", "user_risk_7d", "if_anomaly_score"]
    if "top_reasons" in today.columns:
        columns.append("top_reasons")
    return today.nlargest(n, "user_risk_7d")[columns].reset_index(drop=True)
