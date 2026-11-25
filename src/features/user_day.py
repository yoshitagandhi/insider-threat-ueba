import pandas as pd


def _to_day(df: pd.DataFrame) -> pd.Series:
    return df["date"].dt.date


def logon_features(logon: pd.DataFrame) -> pd.DataFrame:
    """Daily login behaviour, built from Logon rows only (Logoff rows are ignored).

    distinct_pcs counts how many different machines the user logged into that
    day. Logging into a colleague's or supervisor's PC is a classic insider signal.
    """
    logon = logon.copy()
    logon["day"] = _to_day(logon)
    logon["hour"] = logon["date"].dt.hour
    is_logon = logon["activity"].str.lower().eq("logon")

    logon_events = logon[is_logon].copy()
    grouped = logon_events.groupby(["user", "day"])
    features = grouped.agg(
        logon_count=("id", "count"),
        first_logon_hour=("hour", "min"),
        last_logon_hour=("hour", "max"),
        distinct_pcs=("pc", "nunique"),
    ).reset_index()

    after_hours = logon[
        is_logon & ((logon["hour"] < 6) | (logon["hour"] >= 20))
    ]

    ah_counts = (
        after_hours.groupby(["user", "day"])
        .size()
        .rename("after_hours_logon_count")
    )

    features = features.merge(
        ah_counts,
        on=["user", "day"],
        how="left"
    )

    features["after_hours_logon_count"] = (
        features["after_hours_logon_count"].fillna(0)
    )

    return features


def device_features(device: pd.DataFrame) -> pd.DataFrame:
    device = device.copy()
    device["day"] = _to_day(device)
    is_connect = device["activity"].str.lower().eq("connect")

    counts = (
        device.groupby(["user", "day"])
        .size()
        .rename("device_event_count")
        .reset_index()
    )

    connects = (
        device[is_connect]
        .groupby(["user", "day"])
        .size()
        .rename("usb_connect_count")
    )

    counts = counts.merge(
        connects,
        on=["user", "day"],
        how="left"
    )

    counts["usb_connect_count"] = counts["usb_connect_count"].fillna(0)

    return counts


def file_features(file_df: pd.DataFrame) -> pd.DataFrame:
    file_df = file_df.copy()
    file_df["day"] = _to_day(file_df)

    grouped = file_df.groupby(["user", "day"])

    return grouped.agg(
        file_event_count=("id", "count"),
        unique_filenames=("filename", "nunique"),
    ).reset_index()


def email_features(email_df: pd.DataFrame) -> pd.DataFrame:
    email_df = email_df.copy()
    email_df["day"] = _to_day(email_df)

    recipient_columns = ["to", "cc", "bcc"]
    missing = set(recipient_columns).difference(email_df.columns)
    if missing:
        raise ValueError(f"email data is missing recipient columns: {sorted(missing)}")

    recipients = email_df[recipient_columns].fillna("").agg(";".join, axis=1).str.split(";")
    recipients = recipients.apply(lambda values: [value.strip() for value in values if value.strip()])
    email_df["recipient_count"] = recipients.str.len()
    email_df["external_count"] = recipients.apply(
        lambda values: sum("@dtaa.com" not in value.lower() for value in values)
    )

    grouped = email_df.groupby(["user", "day"])

    features = grouped.agg(
        email_count=("id", "count"),
        total_attachments=("attachments", "sum"),
        avg_size=("size", "mean"),
        total_recipients=("recipient_count", "sum"),
        total_external=("external_count", "sum"),
    ).reset_index()

    features["external_recipient_ratio"] = (
        features["total_external"]
        / features["total_recipients"].replace(0, pd.NA)
    ).fillna(0)

    return features.drop(
        columns=["total_recipients", "total_external"]
    )


def http_features(raw_path, chunksize: int = 500_000) -> pd.DataFrame:
    """Experimental HTTP features, deliberately not wired into run_pipeline().

    Re-benchmark these before making any performance claim about HTTP features.
    """
    parts = []

    usecols = ["id", "date", "user", "url"]

    for chunk in pd.read_csv(
        raw_path,
        usecols=usecols,
        parse_dates=["date"],
        chunksize=chunksize
    ):
        chunk["day"] = chunk["date"].dt.date
        chunk["domain"] = chunk["url"].str.extract(
            r"https?://([^/]+)/?"
        )[0]

        agg = chunk.groupby(["user", "day"]).agg(
            http_event_count=("id", "count"),
            domains=("domain", lambda values: set(values.dropna())),
        ).reset_index()

        parts.append(agg)

    combined = pd.concat(parts, ignore_index=True)

    result = combined.groupby(["user", "day"]).agg(
        http_event_count=("http_event_count", "sum"),
        unique_domains=("domains", lambda sets: len(set().union(*sets))),
    ).reset_index()
    return result
