import numpy as np
import pandas as pd
import pytest

from src.sensor_anomaly import score_readings, train_model
from src.sensor_validation import (
    acceptance_criteria,
    evaluate_controlled_events,
    evaluate_perturbation_grid,
    temporal_validation,
)


def fixture(rows=240):
    rng = np.random.default_rng(17)
    return pd.DataFrame({
        "id": range(rows),
        "device_id": "ESP32_TESTE",
        "data_hora": pd.date_range("2026-10-01", periods=rows, freq="5min", tz="UTC"),
        "ph_value": 7 + rng.normal(0, 0.03, rows),
        "turbidity_value": 8 + rng.normal(0, 0.05, rows),
        "tds_value": 30 + rng.normal(0, 0.08, rows),
        "temperature_value": 24 + rng.normal(0, 0.02, rows),
    })


def test_temporal_validation_never_overlaps_training_and_validation():
    evaluation = temporal_validation(fixture(), reference_end="2026-10-02T00:00:00Z")
    assert evaluation.training["data_hora"].max() < evaluation.validation["data_hora"].min()
    assert evaluation.summary["reference_rows"] == 239
    assert evaluation.summary["training_rows"] + evaluation.summary["validation_rows"] == 239


def test_grid_contains_natural_single_and_multivariate_scenarios():
    evaluation = temporal_validation(fixture(), reference_end="2026-10-02T00:00:00Z")
    results = evaluate_perturbation_grid(evaluation)
    assert len(results) == 24
    assert set(results["scenario"]) == {"natural", "single_sensor", "multivariate"}
    assert results["detection_rate"].between(0, 1).all()
    criteria = acceptance_criteria(results)
    assert len(criteria) == 7
    assert criteria["passed"].dtype == bool


def test_controlled_events_are_evaluated_by_time_window():
    frame = fixture()
    trained = train_model(frame, reference_end="2026-10-02T00:00:00Z")
    scored = score_readings(trained.bundle, frame)
    flagged_at = scored.loc[scored["is_anomaly"].notna(), "data_hora"].iloc[5]
    scored.loc[scored["data_hora"].eq(flagged_at), "is_anomaly"] = True
    events = pd.DataFrame([{
        "event_id": "E01",
        "start_at": flagged_at - pd.Timedelta(minutes=1),
        "end_at": flagged_at + pd.Timedelta(minutes=1),
        "expected_sensor": "tds_value",
    }])
    result = evaluate_controlled_events(scored, events)
    assert bool(result.iloc[0]["detected"])
    assert result.iloc[0]["flags"] == 1


def test_controlled_event_contract_rejects_missing_columns():
    with pytest.raises(ValueError, match="Colunas ausentes"):
        evaluate_controlled_events(pd.DataFrame(), pd.DataFrame({"event_id": ["x"]}))
