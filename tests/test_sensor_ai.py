import pandas as pd

from frontend.sensor_ai import summarize_sensor_ai


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
