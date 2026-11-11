"""Carregamento e inferência da IA exploratória dos sensores.

Este módulo não abre conexão com o banco. Ele recebe as leituras já consultadas
pelo dashboard e aplica o artefato versionado em modo somente leitura.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.sensor_anomaly import score_readings

DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "sensor_anomaly"
    / "isolation_forest_v1.joblib"
)


def load_sensor_ai_bundle(path: str | Path = DEFAULT_ARTIFACT) -> dict[str, Any]:
    """Carrega e valida minimamente o artefato antes da inferência."""
    artifact = Path(path)
    if not artifact.is_file():
        raise FileNotFoundError(f"Artefato da IA dos sensores não encontrado: {artifact}")
    bundle = joblib.load(artifact)
    if not isinstance(bundle, dict) or not {"model", "metadata"}.issubset(bundle):
        raise ValueError("Artefato da IA dos sensores inválido.")
    return bundle


def run_sensor_ai(bundle: dict[str, Any], readings: pd.DataFrame) -> pd.DataFrame:
    """Executa a inferência sem persistir ou alterar as leituras de origem."""
    if readings.empty:
        return readings.copy()
    return score_readings(bundle, readings)


def summarize_sensor_ai(scored: pd.DataFrame) -> dict[str, Any] | None:
    """Resume apenas inferências elegíveis; indisponível nunca vira normal."""
    required = {"data_hora", "anomaly_score", "is_anomaly", "classificacao_ia"}
    if scored.empty or not required.issubset(scored):
        return None
    eligible = scored.loc[
        scored["anomaly_score"].notna() & scored["is_anomaly"].notna()
    ].copy()
    if eligible.empty:
        return None
    latest = eligible.sort_values("data_hora").iloc[-1]
    anomalies = int(eligible["is_anomaly"].eq(True).sum())
    return {
        "eligible": len(eligible),
        "anomalies": anomalies,
        "flag_rate": anomalies / len(eligible),
        "latest_at": latest["data_hora"],
        "latest_score": float(latest["anomaly_score"]),
        "latest_is_anomaly": bool(latest["is_anomaly"]),
        "latest_classification": str(latest["classificacao_ia"]),
        "latest_change": str(latest.get("maior_mudanca", "")),
        "model_version": str(latest.get("model_version", "")),
    }
