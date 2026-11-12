import numpy as np
import pandas as pd

from src.sensor_challenger_v2 import (
    challenger_bundle,
    evaluate_perturbation_grid_v2,
    score_challenger,
    temporal_validation_v2,
)
from src.sensor_validation import acceptance_criteria


def fixture(rows=360):
    rng = np.random.default_rng(29)
    return pd.DataFrame({
        "id": range(rows),
        "device_id": "ESP32_TESTE",
        "data_hora": pd.date_range("2026-10-01", periods=rows, freq="5min", tz="UTC"),
        "ph_value": 7 + rng.normal(0, 0.03, rows),
        "turbidity_value": 8 + rng.normal(0, 0.05, rows),
        "tds_value": 30 + rng.normal(0, 0.08, rows),
        "temperature_value": 24 + rng.normal(0, 0.02, rows),
    })


def test_challenger_uses_three_disjoint_temporal_blocks():
    evaluation = temporal_validation_v2(fixture(), reference_end="2026-10-03T00:00:00Z")
    assert evaluation.fit["data_hora"].max() < evaluation.calibration["data_hora"].min()
    assert evaluation.calibration["data_hora"].max() < evaluation.test["data_hora"].min()
    assert evaluation.summary["reference_rows"] == 359
    assert 0 <= evaluation.threshold <= 1


def test_challenger_grid_is_compatible_with_predefined_criteria():
    evaluation = temporal_validation_v2(fixture(), reference_end="2026-10-03T00:00:00Z")
    results = evaluate_perturbation_grid_v2(evaluation)
    assert len(results) == 24
    assert results["detection_rate"].between(0, 1).all()
    criteria = acceptance_criteria(results)
    assert len(criteria) == 7


def test_challenger_bundle_scores_only_eligible_rows():
    frame = fixture()
    evaluation = temporal_validation_v2(frame, reference_end="2026-10-03T00:00:00Z")
    scored = score_challenger(challenger_bundle(evaluation), frame)
    assert pd.isna(scored.iloc[0]["is_anomaly_v2"])
    assert scored.loc[scored["ia_elegivel"], "is_anomaly_v2"].notna().all()
    assert scored["model_version_v2"].nunique() == 1
