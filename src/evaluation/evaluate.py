import pandas as pd
from sklearn.metrics import precision_recall_curve, auc, precision_score, recall_score, f1_score

from src.evaluation.ground_truth import load_ground_truth


def attach_labels(scored: pd.DataFrame) -> pd.DataFrame:
    labels = load_ground_truth()
    merged = scored.merge(labels, on=["user", "day"], how="left")
    merged["is_malicious"] = merged["is_malicious"].fillna(0).astype(int)
    return merged


def evaluate_scores(merged: pd.DataFrame, score_col: str, threshold: float) -> dict:
    y_true = merged["is_malicious"]
    y_pred = (merged[score_col] >= threshold).astype(int)

    precision, recall, _ = precision_recall_curve(y_true, merged[score_col])
    pr_auc = auc(recall, precision)

    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "pr_auc": pr_auc,
        "n_flagged": int(y_pred.sum()),
        "n_malicious_days": int(y_true.sum()),
    }