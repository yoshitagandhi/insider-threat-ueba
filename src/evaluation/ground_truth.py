import glob
import pandas as pd

from src.utils.config import ROOT_DIR

ANSWERS_DIR = ROOT_DIR / "data" / "answers" / "r4.2"


def load_ground_truth() -> pd.DataFrame:
    rows = []

    for path in glob.glob(str(ANSWERS_DIR / "*" / "*.csv")):
        scenario_group = path.replace("\\", "/").split("/")[-2]

        df = pd.read_csv(
            path,
            header=None,
            usecols=[0, 2, 3],
            names=["event_type", "date", "user"],
            parse_dates=["date"],
            engine="python",
        )

        df["scenario_group"] = scenario_group
        rows.append(df)

    all_events = pd.concat(rows, ignore_index=True)

    all_events["day"] = all_events["date"].dt.date

    labels = all_events[
        ["user", "day", "scenario_group"]
    ].drop_duplicates(
        subset=["user", "day"]
    )

    labels["is_malicious"] = 1

    return labels