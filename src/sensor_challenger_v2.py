"""Challenger supervisionado por perturbações sintéticas da telemetria IoT.

O modelo aprende a separar mudanças naturais de alterações artificiais conhecidas.
Isso testa sensibilidade técnica; não cria rótulos sanitários nem comprova detecção
de leptospirose, contaminação ou falha física real.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier

from src.sensor_anomaly import (
    DEFAULT_RANDOM_STATE,
    FEATURE_COLUMNS,
    SENSOR_COLUMNS,
    SYNTHETIC_PERTURBATIONS,
    prepare_sensor_features,
)
from src.sensor_validation import MULTIVARIATE_SCALES, PERTURBATION_GRID

MODEL_VERSION = "sensor_extratrees_synthetic_v2_20261111"
FIT_FRACTION = 0.60
CALIBRATION_FRACTION = 0.20
CALIBRATION_QUANTILE = 0.95
TRAINING_MAGNITUDE_RANGES = {
    "ph_value": (0.5, 2.5),
    "turbidity_value": (5.0, 30.0),
    "tds_value": (7.0, 40.0),
    "temperature_value": (0.75, 3.0),
}


@dataclass(frozen=True)
class ChallengerValidation:
    model: ExtraTreesClassifier
    threshold: float
    fit: pd.DataFrame
    calibration: pd.DataFrame
    test: pd.DataFrame
    summary: dict[str, Any]


def build_challenger() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=600,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=DEFAULT_RANDOM_STATE,
        n_jobs=-1,
    )


def _training_matrix(natural: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Gera treino determinístico; magnitudes contínuas diferem da grade de teste."""
    rng = np.random.default_rng(DEFAULT_RANDOM_STATE)
    base = natural.loc[:, FEATURE_COLUMNS].reset_index(drop=True)
    frames = [base.copy()]
    labels = [np.zeros(len(base), dtype=np.int8)]
    for sensor, (low, high) in TRAINING_MAGNITUDE_RANGES.items():
        synthetic = base.iloc[rng.permutation(len(base))].reset_index(drop=True)
        synthetic[f"delta_{sensor}"] += (
            rng.choice((-1.0, 1.0), len(base)) * rng.uniform(low, high, len(base))
        )
        frames.append(synthetic)
        labels.append(np.ones(len(base), dtype=np.int8))
    combined = base.copy()
    for sensor, strong_magnitude in SYNTHETIC_PERTURBATIONS.items():
        combined[f"delta_{sensor}"] += (
            rng.choice((-1.0, 1.0), len(base))
            * rng.uniform(0.3, 0.8, len(base))
            * strong_magnitude
        )
    frames.append(combined)
    labels.append(np.ones(len(base), dtype=np.int8))
    return pd.concat(frames, ignore_index=True), np.concatenate(labels)


def temporal_validation_v2(
    frame: pd.DataFrame,
    *,
    reference_end: str | pd.Timestamp = "2026-11-04T00:00:00Z",
) -> ChallengerValidation:
    """Separa ajuste, calibração natural e teste final em ordem temporal."""
    featured = prepare_sensor_features(frame)
    cutoff = pd.Timestamp(reference_end)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    reference = featured.loc[
        featured["ia_elegivel"] & featured["data_hora"].lt(cutoff)
    ].reset_index(drop=True)
    if len(reference) < 150:
        raise ValueError("São necessárias ao menos 150 mudanças válidas para o challenger.")
    fit_end = int(len(reference) * FIT_FRACTION)
    calibration_end = int(len(reference) * (FIT_FRACTION + CALIBRATION_FRACTION))
    fit = reference.iloc[:fit_end].copy()
    calibration = reference.iloc[fit_end:calibration_end].copy()
    test = reference.iloc[calibration_end:].copy()
    if min(len(fit), len(calibration), len(test)) == 0:
        raise ValueError("A divisão temporal do challenger produziu um bloco vazio.")

    training_x, training_y = _training_matrix(fit)
    model = build_challenger()
    model.fit(training_x, training_y)
    calibration_probability = model.predict_proba(
        calibration.loc[:, FEATURE_COLUMNS]
    )[:, 1]
    threshold = float(np.quantile(calibration_probability, CALIBRATION_QUANTILE))
    natural_probability = model.predict_proba(test.loc[:, FEATURE_COLUMNS])[:, 1]
    summary = {
        "model_version": MODEL_VERSION,
        "reference_rows": len(reference),
        "fit_natural_rows": len(fit),
        "fit_total_rows_after_augmentation": len(training_x),
        "calibration_rows": len(calibration),
        "test_rows": len(test),
        "fit_end": fit["data_hora"].max(),
        "calibration_start": calibration["data_hora"].min(),
        "calibration_end": calibration["data_hora"].max(),
        "test_start": test["data_hora"].min(),
        "test_end": test["data_hora"].max(),
        "calibration_quantile": CALIBRATION_QUANTILE,
        "decision_threshold": threshold,
        "natural_test_flag_rate": float(np.mean(natural_probability > threshold)),
    }
    return ChallengerValidation(model, threshold, fit, calibration, test, summary)


def _measure(
    evaluation: ChallengerValidation, features: pd.DataFrame
) -> tuple[float, float, float]:
    probabilities = evaluation.model.predict_proba(features.loc[:, FEATURE_COLUMNS])[:, 1]
    return (
        float(np.mean(probabilities > evaluation.threshold)),
        float(np.median(probabilities)),
        float(np.quantile(probabilities, 0.9)),
    )


def evaluate_perturbation_grid_v2(evaluation: ChallengerValidation) -> pd.DataFrame:
    """Aplica a grade fixa exclusivamente no bloco temporal de teste."""
    base = evaluation.test.loc[:, FEATURE_COLUMNS].copy()
    baseline_rate, baseline_median, baseline_p90 = _measure(evaluation, base)
    rows = [{
        "scenario": "natural",
        "sensor": "none",
        "magnitude": 0.0,
        "detection_rate": baseline_rate,
        "lift_vs_natural": 0.0,
        "median_probability": baseline_median,
        "p90_probability": baseline_p90,
    }]
    signs = np.where(np.arange(len(base)) % 2 == 0, 1.0, -1.0)
    for sensor, magnitudes in PERTURBATION_GRID.items():
        for magnitude in magnitudes:
            synthetic = base.copy()
            synthetic[f"delta_{sensor}"] += signs * magnitude
            rate, median, p90 = _measure(evaluation, synthetic)
            rows.append({
                "scenario": "single_sensor",
                "sensor": sensor,
                "magnitude": float(magnitude),
                "detection_rate": rate,
                "lift_vs_natural": rate - baseline_rate,
                "median_probability": median,
                "p90_probability": p90,
            })
    for scale in MULTIVARIATE_SCALES:
        synthetic = base.copy()
        for offset, (sensor, magnitude) in enumerate(SYNTHETIC_PERTURBATIONS.items()):
            synthetic[f"delta_{sensor}"] += np.roll(signs, offset) * magnitude * scale
        rate, median, p90 = _measure(evaluation, synthetic)
        rows.append({
            "scenario": "multivariate",
            "sensor": "all",
            "magnitude": float(scale),
            "detection_rate": rate,
            "lift_vs_natural": rate - baseline_rate,
            "median_probability": median,
            "p90_probability": p90,
        })
    return pd.DataFrame(rows)


def challenger_bundle(evaluation: ChallengerValidation) -> dict[str, Any]:
    metadata = {
        **evaluation.summary,
        "algorithm": "ExtraTreesClassifier",
        "feature_columns": list(FEATURE_COLUMNS),
        "sensor_columns": list(SENSOR_COLUMNS),
        "training_magnitude_ranges": TRAINING_MAGNITUDE_RANGES,
        "random_state": DEFAULT_RANDOM_STATE,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "challenger_offline; nao promovido ao dashboard",
        "scope": "sensibilidade a perturbacoes sinteticas; sem significado sanitario",
    }
    return {"model": evaluation.model, "threshold": evaluation.threshold, "metadata": metadata}


def score_challenger(bundle: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Pontua novas leituras sem alterar o classificador V1 do dashboard."""
    expected = tuple(bundle.get("metadata", {}).get("feature_columns", ()))
    if expected != FEATURE_COLUMNS or "model" not in bundle or "threshold" not in bundle:
        raise ValueError("Artefato challenger V2 inválido.")
    result = prepare_sensor_features(frame)
    result["anomaly_probability_v2"] = np.nan
    result["is_anomaly_v2"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    eligible = result["ia_elegivel"]
    if eligible.any():
        probability = bundle["model"].predict_proba(
            result.loc[eligible, FEATURE_COLUMNS]
        )[:, 1]
        result.loc[eligible, "anomaly_probability_v2"] = probability
        result.loc[eligible, "is_anomaly_v2"] = probability > float(bundle["threshold"])
    result["model_version_v2"] = bundle["metadata"]["model_version"]
    return result
