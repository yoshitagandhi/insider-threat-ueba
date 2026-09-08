import pandas as pd


def categorize_errors(
    merged: pd.DataFrame,
    score_col: str,
    threshold: float
) -> pd.DataFrame:
    df = merged.copy()
    df["predicted"] = (df[score_col] >= threshold).astype(int)

    def label(row):
        if row["predicted"] == 1 and row["is_malicious"] == 1:
            return "true_positive"
        if row["predicted"] == 1 and row["is_malicious"] == 0:
            return "false_positive"
        if row["predicted"] == 0 and row["is_malicious"] == 1:
            return "false_negative"
        return "true_negative"

    df["error_type"] = df.apply(label, axis=1)
    return df


def top_contributing_features(
    row: pd.Series,
    zscore_cols: list[str],
    n: int = 3
) -> list[str]:
    values = row[zscore_cols].abs().sort_values(ascending=False)
    return list(values.head(n).index)


def summarize_errors(
    df: pd.DataFrame,
    zscore_cols: list[str]
) -> pd.DataFrame:
    interesting = df[
        df["error_type"].isin(["false_positive", "false_negative"])
    ].copy()

    interesting["top_features"] = interesting.apply(
        lambda r: top_contributing_features(r, zscore_cols),
        axis=1
    )

    return interesting[
        ["user", "day", "error_type", "if_anomaly_score", "top_features"]
    ]