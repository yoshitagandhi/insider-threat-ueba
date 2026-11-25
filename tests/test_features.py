import pandas as pd
from src.features.user_day import device_features, email_features, file_features, logon_features


def test_logon_features_counts_correctly():
    logon = pd.DataFrame({
        "id": ["1", "2", "3"],
        "date": pd.to_datetime(["2010-01-01 09:00", "2010-01-01 23:00", "2010-01-02 09:00"]),
        "user": ["A", "A", "A"],
        "pc": ["PC1", "PC1", "PC1"],
        "activity": ["Logon", "Logon", "Logon"],
    })
    result = logon_features(logon)
    day1 = result[result["day"] == pd.Timestamp("2010-01-01").date()].iloc[0]
    assert day1["logon_count"] == 2
    assert day1["after_hours_logon_count"] == 1


def test_logon_features_exclude_logoff_events():
    logon = pd.DataFrame({
        "id": ["1", "2"],
        "date": pd.to_datetime(["2010-01-01 09:00", "2010-01-01 22:00"]),
        "user": ["A", "A"],
        "pc": ["PC1", "PC1"],
        "activity": ["Logon", "Logoff"],
    })
    result = logon_features(logon).iloc[0]
    assert result["logon_count"] == 1
    assert result["first_logon_hour"] == 9
    assert result["last_logon_hour"] == 9


def test_device_features_handles_no_connects():
    device = pd.DataFrame({
        "id": ["1"],
        "date": pd.to_datetime(["2010-01-01 09:00"]),
        "user": ["A"],
        "pc": ["PC1"],
        "activity": ["Disconnect"],
    })
    result = device_features(device)
    assert result.iloc[0]["usb_connect_count"] == 0
    assert result.iloc[0]["device_event_count"] == 1


def test_email_features_include_cc_and_bcc_recipients():
    email = pd.DataFrame({
        "id": ["1"],
        "date": pd.to_datetime(["2010-01-01 09:00"]),
        "user": ["A"],
        "to": ["internal@dtaa.com"],
        "cc": ["external@example.com"],
        "bcc": ["second@example.com"],
        "attachments": [1],
        "size": [10],
    })
    result = email_features(email).iloc[0]
    assert result["external_recipient_ratio"] == 2 / 3


def test_logon_features_count_distinct_pcs():
    logon = pd.DataFrame({
        "id": ["1", "2", "3"],
        "date": pd.to_datetime(["2010-01-01 09:00", "2010-01-01 11:00", "2010-01-01 13:00"]),
        "user": ["A", "A", "A"],
        "pc": ["PC1", "PC2", "PC1"],
        "activity": ["Logon", "Logon", "Logon"],
    })
    result = logon_features(logon).iloc[0]
    assert result["distinct_pcs"] == 2


def test_after_hours_usb_and_file_counts():
    device = pd.DataFrame({
        "id": ["1", "2"],
        "date": pd.to_datetime(["2010-01-01 10:00", "2010-01-01 22:30"]),
        "user": ["A", "A"],
        "pc": ["PC1", "PC1"],
        "activity": ["Connect", "Connect"],
    })
    files = pd.DataFrame({
        "id": ["1", "2", "3"],
        "date": pd.to_datetime(["2010-01-01 03:00", "2010-01-01 12:00", "2010-01-01 21:00"]),
        "user": ["A", "A", "A"],
        "pc": ["PC1", "PC1", "PC1"],
        "filename": ["a", "b", "c"],
    })

    usb = device_features(device).iloc[0]
    file_day = file_features(files).iloc[0]

    assert usb["usb_connect_count"] == 2
    assert usb["after_hours_usb_count"] == 1
    assert file_day["after_hours_file_count"] == 2
