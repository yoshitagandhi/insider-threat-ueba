from src.baselines.personal_baseline import FEATURE_COLS, NOVELTY_COLS
from src.evaluation.analysis import FEATURE_GROUPS, model_columns
from src.models.isolation_forest_model import MODEL_COLS


def test_every_model_input_belongs_to_a_feature_group():
    grouped = set()
    for group, features in FEATURE_GROUPS.items():
        if group.startswith("New features"):
            continue
        grouped.update(features)

    assert grouped == set(FEATURE_COLS) | set(NOVELTY_COLS)


def test_model_columns_maps_features_to_model_inputs():
    columns = model_columns(["usb_connect_count", "first_usb_ever"])

    assert columns == ["usb_connect_count_zscore", "first_usb_ever"]
    assert set(columns) <= set(MODEL_COLS)
