import pandas as pd

from src.utils.config import DATA_PROCESSED_DIR, DATA_RAW_DIR, MODELS_DIR
from src.data.loaders import load_event_data
from src.features.user_day import logon_features, device_features, file_features, email_features
from src.baselines.personal_baseline import merge_daily_features, add_personal_baseline
from src.baselines.deviation import add_deviation_features, add_top_reasons, statistical_anomaly_score
from src.models.feature_selection import save_selection, select_features
from src.models.isolation_forest_model import (
    fit_isolation_forest,
    save_isolation_forest,
    score_isolation_forest,
    split_by_date,
)
from src.models.rules import add_hybrid_score
from src.models.user_risk import add_user_risk
from src.evaluation.evaluate import attach_labels

SELECTION_PATH = MODELS_DIR / "selected_features.json"


def run_pipeline(persist_model: bool = False) -> pd.DataFrame:
    """Build features, choose inputs on validation, fit on the earlier period, score every day.

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
    daily = attach_labels(daily)

    train, _, cutoff = split_by_date(daily)

    best, columns, selection_table = select_features(train)
    print(selection_table.to_string(index=False))
    print(f"Selected feature set: {best}")
    save_selection(best, columns, selection_table, SELECTION_PATH)

    print(f"Training Isolation Forest on days before {cutoff}")
    model = fit_isolation_forest(train, columns=columns)
    if persist_model:
        save_isolation_forest(model, MODELS_DIR / "isolation_forest.joblib")

    scored = score_isolation_forest(model, daily, columns=columns)
    scored["split"] = (scored["day"] < cutoff).map({True: "train", False: "test"})
    scored = add_hybrid_score(scored)
    scored = add_top_reasons(scored)
    scored = add_user_risk(scored)

    skipped = len(daily) - len(scored)
    print(f"Skipped {skipped} cold-start user-days that have no baseline yet")
    print(f"Rule fired on {int(scored['rule_alert'].sum())} user-days")

    return scored


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
