import pandas as pd

from frontend.sensor_ai import summarize_sensor_ai


def test_frozen_comparison_preserves_source_and_unavailable_rows():
    from frontend.sensor_ai import (
        compare_sensor_models, load_sensor_ai_bundle, load_sensor_challenger_bundle,
    )
    dates = pd.to_datetime([
        "2026-11-15T14:07:00Z", "2026-11-15T14:07:06Z",
        "2026-11-15T14:30:00Z", "2026-11-15T14:30:06Z",
    ])
    frame = pd.DataFrame({
        "id": [1, 2, 3, 4], "device_id": "ESP32_TEST",
        "data_hora": dates, "ph_value": [7., 7.01, 7.02, 8.],
        "turbidity_value": [10., 10., 10., 30.],
        "tds_value": [100., 100., 100., 300.],
        "temperature_value": [24., 24., 24., 25.],
    }).iloc[::-1].copy()
    before = frame.copy(deep=True)
    result = compare_sensor_models(
        load_sensor_ai_bundle(), load_sensor_challenger_bundle(), frame,
    )
    pd.testing.assert_frame_equal(frame, before)
    assert result["id"].tolist() == [1, 2, 3, 4]
    assert result["concordancia"].notna().tolist() == [False, True, False, True]
    assert result.loc[result["id"].isin([1, 3]), "is_anomaly_v2"].isna().all()
    assert result["model_version"].str.contains("iforest").all()
    assert result["model_version_v2"].str.contains("extratrees").all()


def test_summary_does_not_treat_unavailable_as_normal():
    frame = pd.DataFrame({
        "data_hora": pd.date_range("2026-11-01", periods=3, freq="5min", tz="UTC"),
        "anomaly_score": [None, -0.2, 0.1],
        "is_anomaly": pd.array([pd.NA, False, True], dtype="boolean"),
        "classificacao_ia": ["indisponivel", "comportamento_historico", "alteracao_incomum"],
        "maior_mudanca": [pd.NA, "ph_value", "tds_value"],
        "model_version": ["v1", "v1", "v1"],
    })
    summary = summarize_sensor_ai(frame)
    assert summary is not None
    assert summary["eligible"] == 2
    assert summary["anomalies"] == 1
    assert summary["flag_rate"] == 0.5
    assert summary["latest_is_anomaly"] is True
    assert summary["latest_change"] == "tds_value"


def test_summary_is_none_without_eligible_inference():
    frame = pd.DataFrame({
        "data_hora": [pd.Timestamp("2026-11-01", tz="UTC")],
        "anomaly_score": [None],
        "is_anomaly": pd.array([pd.NA], dtype="boolean"),
        "classificacao_ia": ["indisponivel"],
    })
    assert summarize_sensor_ai(frame) is None
