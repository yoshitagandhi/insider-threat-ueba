"""Reusable, publication-ready visuals for imbalanced anomaly detection."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix, precision_recall_curve

from src.evaluation.evaluate import evaluate_scores


def plot_precision_recall_comparison(
    scored: pd.DataFrame,
    score_columns: dict[str, str],
):
    fig, ax = plt.subplots(figsize=(7, 5))
    y_true = scored["is_malicious"]
    for label, score_column in score_columns.items():
        precision, recall, _ = precision_recall_curve(y_true, scored[score_column])
        ax.plot(recall, precision, linewidth=2, label=label)
    ax.set(xlabel="Recall", ylabel="Precision", title="Precision–recall comparison")
    ax.legend()
    ax.grid(alpha=0.25)
    return fig


def threshold_sensitivity(
    scored: pd.DataFrame,
    score_column: str,
    percentiles: tuple[float, ...] = (95, 97, 99, 99.5),
) -> pd.DataFrame:
    rows = []
    for percentile in percentiles:
        threshold = float(np.percentile(scored[score_column], percentile))
        metrics = evaluate_scores(scored, score_column, threshold)
        rows.append({"percentile": percentile, "threshold": threshold, **metrics})
    return pd.DataFrame(rows)


def plot_confusion_matrix(scored: pd.DataFrame, score_column: str, threshold: float):
    predictions = (scored[score_column] >= threshold).astype(int)
    matrix = confusion_matrix(scored["is_malicious"], predictions)
    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay(matrix, display_labels=["Benign", "Malicious"]).plot(
        ax=ax,
        colorbar=False,
    )
    ax.set_title("Confusion matrix at alert threshold")
    return fig


def plot_class_balance(scored: pd.DataFrame):
    counts = scored["is_malicious"].map({0: "Benign", 1: "Malicious"}).value_counts()
    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(counts.index, counts.values, color=["#4477AA", "#CC6677"])
    ax.set(title="Class imbalance in scored user-days", ylabel="Days")
    ax.bar_label(bars, labels=[f"{value:,}" for value in counts.values])
    return fig
