import numpy as np
import pandas as pd
import pytest

from src.sensor_anomaly import (
    FEATURE_COLUMNS,
    MODEL_VERSION,
    prepare_sensor_features,
    score_readings,
    train_model,
)


def fixture(rows=180):
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "id": range(rows),
        "device_id": "ESP32_TESTE",
        "data_hora": pd.date_range("2026-10-01", periods=rows, freq="5min", tz="UTC"),
        "ph_value": 7 + rng.normal(0, .02, rows),
        "turbidity_value": 1 + rng.normal(0, .01, rows),
        "tds_value": 30 + rng.normal(0, .02, rows),
        "temperature_value": 24 + rng.normal(0, .01, rows),
    })


def test_features_are_causal_and_do_not_cross_gap():
    frame = fixture(4)
    frame.loc[3, "data_hora"] += pd.Timedelta(hours=1)
    result = prepare_sensor_features(frame)
    assert not result.iloc[0]["ia_elegivel"]
    assert result.iloc[1]["delta_ph_value"] == pytest.approx(
        frame.iloc[1]["ph_value"] - frame.iloc[0]["ph_value"]
    )
    assert not result.iloc[3]["ia_elegivel"]


def test_duplicate_timestamp_keeps_last_record():
    frame = fixture(4)
    duplicate = frame.iloc[[1]].copy()
    duplicate["id"] = 99
    duplicate["ph_value"] = 9
    result = prepare_sensor_features(pd.concat([frame, duplicate]))
    assert len(result) == 4
    assert result.loc[result["data_hora"].eq(frame.iloc[1]["data_hora"]), "ph_value"].iloc[0] == 9


def test_missing_contract_is_rejected():
    with pytest.raises(ValueError, match="Colunas ausentes"):
        prepare_sensor_features(pd.DataFrame({"device_id": ["x"]}))


def test_training_is_temporal_and_versioned():
    result = train_model(fixture(), reference_end="2026-10-02T00:00:00Z")
    metadata = result.metrics
    assert metadata["model_version"] == MODEL_VERSION
    assert metadata["reference_rows"] == 179
    assert metadata["training_rows_evaluation"] < metadata["reference_rows"]
    assert metadata["validation_start"] > fixture().iloc[0]["data_hora"].isoformat()
    assert set(metadata["synthetic_sensitivity"]) == {
        "ph_value", "turbidity_value", "tds_value", "temperature_value", "multivariada"
    }


def test_scoring_marks_unavailable_first_row_and_scores_following_rows():
    trained = train_model(fixture(), reference_end="2026-10-02T00:00:00Z")
    scored = score_readings(trained.bundle, fixture(20))
    assert scored.iloc[0]["classificacao_ia"] == "indisponivel"
    assert scored.iloc[1:]["anomaly_score"].notna().all()
    assert scored.iloc[1:]["is_anomaly"].notna().all()
    assert scored["model_version"].eq(MODEL_VERSION).all()
    assert tuple(trained.bundle["metadata"]["feature_columns"]) == FEATURE_COLUMNS


def test_invalid_artifact_is_rejected():
    with pytest.raises(ValueError, match="Artefato"):
        score_readings({}, fixture())
