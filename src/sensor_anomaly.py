"""Detecção exploratória de anomalias multivariadas na telemetria IoT.

O modelo analisa mudanças entre leituras consecutivas. Ele não classifica
qualidade da água, não detecta patógenos e não alimenta o Poisson epidemiológico.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

SENSOR_COLUMNS = (
    "ph_value",
    "turbidity_value",
    "tds_value",
    "temperature_value",
)
FEATURE_COLUMNS = tuple(f"delta_{column}" for column in SENSOR_COLUMNS)
MAX_GAP = pd.Timedelta(minutes=7, seconds=30)
DEFAULT_CONTAMINATION = 0.01
DEFAULT_RANDOM_STATE = 20261111
MODEL_VERSION = "sensor_iforest_delta_v1_20261111"
SYNTHETIC_PERTURBATIONS = {
    "ph_value": 3.0,
    "turbidity_value": 40.0,
    "tds_value": 50.0,
    "temperature_value": 4.0,
}


@dataclass(frozen=True)
class TrainingResult:
    bundle: dict[str, Any]
    metrics: dict[str, Any]


def prepare_sensor_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Cria diferenças causais; nunca atravessa dispositivo, lacuna ou duplicata."""
    required = {"device_id", "data_hora", *SENSOR_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Colunas ausentes para a IA dos sensores: " + ", ".join(missing))
    result = frame.copy()
    result["data_hora"] = pd.to_datetime(result["data_hora"], errors="coerce", utc=True)
    for column in SENSOR_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    result = result.dropna(subset=["device_id", "data_hora"])
    sort_columns = ["device_id", "data_hora"] + (["id"] if "id" in result else [])
    result = result.sort_values(sort_columns, kind="stable")
    result = result.drop_duplicates(["device_id", "data_hora"], keep="last")
    gap = result.groupby("device_id", sort=False)["data_hora"].diff()
    result["intervalo_segundos"] = gap.dt.total_seconds()
    consecutive = gap.gt(pd.Timedelta(0)) & gap.le(MAX_GAP)
    for column in SENSOR_COLUMNS:
        result[f"delta_{column}"] = (
            result.groupby("device_id", sort=False)[column].diff().where(consecutive)
        )
    values = result.loc[:, FEATURE_COLUMNS]
    result["ia_elegivel"] = values.notna().all(axis=1)
    return result.reset_index(drop=True)


def build_model(*, contamination: float = DEFAULT_CONTAMINATION) -> Pipeline:
    if not 0 < contamination <= 0.1:
        raise ValueError("contamination deve estar no intervalo (0, 0.1].")
    return Pipeline(
        [
            ("robust_scaler", RobustScaler()),
            (
                "isolation_forest",
                IsolationForest(
                    n_estimators=400,
                    max_samples="auto",
                    contamination=contamination,
                    random_state=DEFAULT_RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _synthetic_scenarios(validation: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Perturbações explícitas para testar sensibilidade; não representam campo."""
    scenarios: dict[str, pd.DataFrame] = {}
    signs = np.where(np.arange(len(validation)) % 2 == 0, 1.0, -1.0)
    for column, magnitude in SYNTHETIC_PERTURBATIONS.items():
        feature = f"delta_{column}"
        synthetic = validation.loc[:, FEATURE_COLUMNS].copy()
        synthetic[feature] = synthetic[feature] + signs * magnitude
        scenarios[column] = synthetic
    combined = validation.loc[:, FEATURE_COLUMNS].copy()
    for index, (column, magnitude) in enumerate(SYNTHETIC_PERTURBATIONS.items()):
        combined[f"delta_{column}"] = combined[f"delta_{column}"] + np.roll(signs, index) * magnitude
    scenarios["multivariada"] = combined
    return scenarios


def train_model(
    frame: pd.DataFrame,
    *,
    reference_end: str | pd.Timestamp = "2026-11-04T00:00:00Z",
    train_fraction: float = 0.8,
    contamination: float = DEFAULT_CONTAMINATION,
) -> TrainingResult:
    """Valida temporalmente e reajusta o artefato final em toda a referência."""
    if not 0.5 <= train_fraction < 1:
        raise ValueError("train_fraction deve estar no intervalo [0.5, 1).")
    featured = prepare_sensor_features(frame)
    cutoff = pd.Timestamp(reference_end)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    reference = featured.loc[
        featured["ia_elegivel"] & featured["data_hora"].lt(cutoff)
    ].copy()
    if len(reference) < 100:
        raise ValueError("São necessárias ao menos 100 mudanças válidas para o treino.")
    split_at = int(len(reference) * train_fraction)
    training = reference.iloc[:split_at]
    validation = reference.iloc[split_at:]
    if validation.empty:
        raise ValueError("A validação temporal ficou vazia.")

    evaluation_model = build_model(contamination=contamination)
    evaluation_model.fit(training.loc[:, FEATURE_COLUMNS])
    natural_flags = evaluation_model.predict(validation.loc[:, FEATURE_COLUMNS]) == -1
    sensitivities = {
        name: float(np.mean(evaluation_model.predict(scenario) == -1))
        for name, scenario in _synthetic_scenarios(validation).items()
    }

    final_model = build_model(contamination=contamination)
    final_model.fit(reference.loc[:, FEATURE_COLUMNS])
    metadata = {
        "model_version": MODEL_VERSION,
        "algorithm": "IsolationForest",
        "feature_columns": list(FEATURE_COLUMNS),
        "sensor_columns": list(SENSOR_COLUMNS),
        "reference_end": cutoff.isoformat(),
        "reference_rows": len(reference),
        "training_rows_evaluation": len(training),
        "validation_rows": len(validation),
        "train_fraction": float(train_fraction),
        "contamination": float(contamination),
        "random_state": DEFAULT_RANDOM_STATE,
        "validation_start": validation["data_hora"].min().isoformat(),
        "validation_end": validation["data_hora"].max().isoformat(),
        "natural_validation_flag_rate": float(np.mean(natural_flags)),
        "synthetic_sensitivity": sensitivities,
        "synthetic_perturbations": SYNTHETIC_PERTURBATIONS,
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "mudancas multivariadas na telemetria; sem significado sanitario",
    }
    bundle = {"model": final_model, "metadata": metadata}
    return TrainingResult(bundle=bundle, metrics=metadata.copy())


def score_readings(bundle: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Aplica o artefato e mantém linhas sem contexto como indisponíveis."""
    if "model" not in bundle or "metadata" not in bundle:
        raise ValueError("Artefato de IA inválido.")
    expected = tuple(bundle["metadata"].get("feature_columns", ()))
    if expected != FEATURE_COLUMNS:
        raise ValueError("O artefato não corresponde às features esperadas.")
    result = prepare_sensor_features(frame)
    result["anomaly_score"] = np.nan
    result["is_anomaly"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    eligible = result["ia_elegivel"]
    if eligible.any():
        features = result.loc[eligible, FEATURE_COLUMNS]
        decision = bundle["model"].decision_function(features)
        prediction = bundle["model"].predict(features)
        result.loc[eligible, "anomaly_score"] = -decision
        result.loc[eligible, "is_anomaly"] = prediction == -1
    result["model_version"] = bundle["metadata"]["model_version"]
    result["classificacao_ia"] = np.select(
        [
            result["is_anomaly"].eq(True).fillna(False).to_numpy(dtype=bool),
            result["is_anomaly"].eq(False).fillna(False).to_numpy(dtype=bool),
        ],
        ["alteracao_incomum", "comportamento_historico"],
        default="indisponivel",
    )
    result["maior_mudanca"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result.loc[eligible, "maior_mudanca"] = (
        result.loc[eligible, FEATURE_COLUMNS]
        .abs()
        .idxmax(axis=1)
        .str.replace("delta_", "", regex=False)
    )
    return result
