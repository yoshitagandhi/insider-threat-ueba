"""Raw CERT event loaders used by the feature pipeline."""

from pathlib import Path

import pandas as pd


def load_event_data(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the four event sources used by the production feature set."""
    logon = pd.read_csv(raw_dir / "logon.csv", parse_dates=["date"])
    device = pd.read_csv(raw_dir / "device.csv", parse_dates=["date"])
    file_df = pd.read_csv(
        raw_dir / "file.csv",
        usecols=["id", "date", "user", "pc", "filename"],
        parse_dates=["date"],
    )
    email_df = pd.read_csv(
        raw_dir / "email.csv",
        usecols=["id", "date", "user", "pc", "to", "cc", "bcc", "size", "attachments"],
        parse_dates=["date"],
    )
    return logon, device, file_df, email_df
