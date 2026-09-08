import matplotlib.pyplot as plt
import pandas as pd


def plot_user_timeline(
    merged: pd.DataFrame,
    user: str,
    score_col: str,
    threshold: float | None = None,
    save_path=None,
):
    user_df = merged[merged["user"] == user].sort_values("day")
    if user_df.empty:
        raise ValueError(f"No rows found for user {user}")

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(user_df["day"], user_df[score_col], color="#4477AA", linewidth=1.2, label=score_col)

    malicious_days = user_df[user_df["is_malicious"] == 1]["day"]
    if not malicious_days.empty:
        for d in malicious_days:
            ax.axvspan(
                d - pd.Timedelta(hours=12),
                d + pd.Timedelta(hours=12),
                color="#CC3333",
                alpha=0.3,
            )

    if threshold is not None:
        ax.axhline(
            threshold,
            color="#DD8452",
            linestyle="--",
            linewidth=1.2,
            label=f"flag threshold ({threshold:.3f})",
        )

    ax.set_title(f"Anomaly score over time — {user}")
    ax.set_xlabel("Date")
    ax.set_ylabel(score_col)
    ax.legend()
    fig.autofmt_xdate()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
