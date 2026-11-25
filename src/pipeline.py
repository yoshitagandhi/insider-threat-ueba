import pandas as pd

from src.utils.config import DATA_PROCESSED_DIR, DATA_RAW_DIR, MODELS_DIR
from src.data.loaders import load_event_data
from src.features.user_day import logon_features, device_features, file_features, email_features
from src.baselines.personal_baseline import merge_daily_features, add_personal_baseline
from src.baselines.deviation import add_deviation_features, add_top_reasons, statistical_anomaly_score
from src.models.isolation_forest_model import (
    fit_isolation_forest,
    save_isolation_forest,
    score_isolation_forest,
    split_by_date,
)
from src.models.user_risk import add_user_risk
from src.evaluation.evaluate import attach_labels


def run_pipeline(persist_model: bool = False) -> pd.DataFrame:
    """Build features, fit on the earlier period, and score every user-day.

    The output has a "split" column ("train" or "test"). Honest evaluation
    should only look at the "test" rows, because the model never saw them.
    """
    logon, device, file_df, email_df = load_event_data(DATA_RAW_DIR)

    daily = merge_daily_features(
        logon_features(logon),
        device_features(device),
        file_features(file_df),
        email_features(email_df),
    )

    daily = add_personal_baseline(daily)
    daily = add_deviation_features(daily)
    daily["stat_anomaly_score"] = statistical_anomaly_score(daily)

    train, _, cutoff = split_by_date(daily)
    print(f"Training Isolation Forest on days before {cutoff}")

    model = fit_isolation_forest(train)
    if persist_model:
        save_isolation_forest(model, MODELS_DIR / "isolation_forest.joblib")

    scored = score_isolation_forest(model, daily)
    scored["split"] = (scored["day"] < cutoff).map({True: "train", False: "test"})
    scored = add_top_reasons(scored)
    scored = add_user_risk(scored)

    skipped = len(daily) - len(scored)
    print(f"Skipped {skipped} cold-start user-days that have no baseline yet")

    return attach_labels(scored)


def main() -> None:
    """Run the production pipeline and write the dashboard-ready data set."""
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_PROCESSED_DIR / "scored_daily.parquet"
    run_pipeline(persist_model=True).to_parquet(output_path, index=False)
    print(f"Wrote scored user-day data to {output_path}")
    print("Next steps: python -m src.evaluation.report")
    print("            python -m src.evaluation.analysis")


if __name__ == "__main__":
    main()
