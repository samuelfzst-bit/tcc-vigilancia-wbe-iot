"""Validação reproduzível da IA exploratória dos sensores.

As métricas deste módulo descrevem resposta a perturbações conhecidas. Elas não
substituem rótulos de campo e não possuem interpretação sanitária.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.sensor_anomaly import (
    DEFAULT_CONTAMINATION,
    FEATURE_COLUMNS,
    SYNTHETIC_PERTURBATIONS,
    build_model,
    prepare_sensor_features,
)

PERTURBATION_GRID = {
    "ph_value": (0.25, 0.5, 1.0, 2.0, 3.0),
    "turbidity_value": (2.0, 5.0, 10.0, 20.0, 40.0),
    "tds_value": (2.0, 5.0, 10.0, 25.0, 50.0),
    "temperature_value": (0.25, 0.5, 1.0, 2.0, 4.0),
}
MULTIVARIATE_SCALES = (0.25, 0.5, 1.0)


@dataclass(frozen=True)
class TemporalValidation:
    model: Any
    training: pd.DataFrame
    validation: pd.DataFrame
    summary: dict[str, Any]


def temporal_validation(
    frame: pd.DataFrame,
    *,
    reference_end: str | pd.Timestamp = "2026-11-04T00:00:00Z",
    train_fraction: float = 0.8,
    contamination: float = DEFAULT_CONTAMINATION,
) -> TemporalValidation:
    """Ajusta somente no passado e reserva o trecho final para avaliação."""
    if not 0.5 <= train_fraction < 1:
        raise ValueError("train_fraction deve estar no intervalo [0.5, 1).")
    featured = prepare_sensor_features(frame)
    cutoff = pd.Timestamp(reference_end)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    reference = featured.loc[
        featured["ia_elegivel"] & featured["data_hora"].lt(cutoff)
    ].copy()
    if len(reference) < 100:
        raise ValueError("São necessárias ao menos 100 mudanças válidas.")
    split_at = int(len(reference) * train_fraction)
    training = reference.iloc[:split_at].copy()
    validation = reference.iloc[split_at:].copy()
    if validation.empty:
        raise ValueError("A validação temporal ficou vazia.")
    model = build_model(contamination=contamination)
    model.fit(training.loc[:, FEATURE_COLUMNS])
    natural_prediction = model.predict(validation.loc[:, FEATURE_COLUMNS])
    natural_score = -model.decision_function(validation.loc[:, FEATURE_COLUMNS])
    summary = {
        "reference_rows": len(reference),
        "training_rows": len(training),
        "validation_rows": len(validation),
        "training_end": training["data_hora"].max(),
        "validation_start": validation["data_hora"].min(),
        "validation_end": validation["data_hora"].max(),
        "natural_flag_rate": float(np.mean(natural_prediction == -1)),
        "natural_score_median": float(np.median(natural_score)),
    }
    return TemporalValidation(model, training, validation, summary)


def _measure(model: Any, features: pd.DataFrame) -> tuple[float, float, float]:
    prediction = model.predict(features)
    scores = -model.decision_function(features)
    return (
        float(np.mean(prediction == -1)),
        float(np.median(scores)),
        float(np.quantile(scores, 0.9)),
    )


def evaluate_perturbation_grid(evaluation: TemporalValidation) -> pd.DataFrame:
    """Mede resposta por intensidade, mantendo a validação temporal intacta."""
    base = evaluation.validation.loc[:, FEATURE_COLUMNS]
    baseline_rate, baseline_median, baseline_p90 = _measure(evaluation.model, base)
    rows = [{
        "scenario": "natural",
        "sensor": "none",
        "magnitude": 0.0,
        "detection_rate": baseline_rate,
        "lift_vs_natural": 0.0,
        "median_score": baseline_median,
        "p90_score": baseline_p90,
    }]
    signs = np.where(np.arange(len(base)) % 2 == 0, 1.0, -1.0)
    for sensor, magnitudes in PERTURBATION_GRID.items():
        feature = f"delta_{sensor}"
        for magnitude in magnitudes:
            synthetic = base.copy()
            synthetic[feature] = synthetic[feature] + signs * magnitude
            rate, median, p90 = _measure(evaluation.model, synthetic)
            rows.append({
                "scenario": "single_sensor",
                "sensor": sensor,
                "magnitude": float(magnitude),
                "detection_rate": rate,
                "lift_vs_natural": rate - baseline_rate,
                "median_score": median,
                "p90_score": p90,
            })
    for scale in MULTIVARIATE_SCALES:
        synthetic = base.copy()
        for offset, (sensor, magnitude) in enumerate(SYNTHETIC_PERTURBATIONS.items()):
            synthetic[f"delta_{sensor}"] = (
                synthetic[f"delta_{sensor}"]
                + np.roll(signs, offset) * magnitude * scale
            )
        rate, median, p90 = _measure(evaluation.model, synthetic)
        rows.append({
            "scenario": "multivariate",
            "sensor": "all",
            "magnitude": float(scale),
            "detection_rate": rate,
            "lift_vs_natural": rate - baseline_rate,
            "median_score": median,
            "p90_score": p90,
        })
    return pd.DataFrame(rows)


def acceptance_criteria(results: pd.DataFrame) -> pd.DataFrame:
    """Critérios pré-definidos; reprovação aponta limite, não invalida o IoT."""
    baseline = float(results.loc[results["scenario"].eq("natural"), "detection_rate"].iloc[0])

    def rate(scenario: str, sensor: str, magnitude: float) -> float:
        row = results.loc[
            results["scenario"].eq(scenario)
            & results["sensor"].eq(sensor)
            & results["magnitude"].eq(magnitude),
            "detection_rate",
        ]
        if row.empty:
            raise ValueError(f"Cenário ausente: {scenario}/{sensor}/{magnitude}")
        return float(row.iloc[0])

    checks = [
        ("Taxa natural ≤ 10%", baseline, 0.10, baseline <= 0.10),
        ("Multivariado moderado ≥ 70%", rate("multivariate", "all", 0.5), 0.70,
         rate("multivariate", "all", 0.5) >= 0.70),
        ("Multivariado forte ≥ 90%", rate("multivariate", "all", 1.0), 0.90,
         rate("multivariate", "all", 1.0) >= 0.90),
    ]
    for sensor, magnitudes in PERTURBATION_GRID.items():
        strong = float(max(magnitudes))
        observed = rate("single_sensor", sensor, strong)
        checks.append((f"{sensor} forte ≥ 50%", observed, 0.50, observed >= 0.50))
    return pd.DataFrame(checks, columns=["criterion", "observed", "target", "passed"])


def evaluate_controlled_events(
    scored: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """Avalia se ao menos uma sinalização ocorreu em cada janela controlada."""
    required = {"event_id", "start_at", "end_at", "expected_sensor"}
    missing = required - set(events)
    if missing:
        raise ValueError("Colunas ausentes no registro de eventos: " + ", ".join(sorted(missing)))
    readings = scored.copy()
    readings["data_hora"] = pd.to_datetime(readings["data_hora"], errors="coerce", utc=True)
    log = events.copy()
    log["start_at"] = pd.to_datetime(log["start_at"], errors="coerce", utc=True)
    log["end_at"] = pd.to_datetime(log["end_at"], errors="coerce", utc=True)
    if log[["start_at", "end_at"]].isna().any().any():
        raise ValueError("O registro de eventos contém horário inválido.")
    output = []
    for event in log.itertuples(index=False):
        window = readings.loc[
            readings["data_hora"].between(event.start_at, event.end_at, inclusive="both")
        ].copy()
        flagged = window.loc[window["is_anomaly"].eq(True)]
        first = flagged["data_hora"].min() if not flagged.empty else pd.NaT
        output.append({
            "event_id": event.event_id,
            "expected_sensor": event.expected_sensor,
            "readings": len(window),
            "flags": len(flagged),
            "detected": not flagged.empty,
            "first_flag_at": first,
            "time_to_detect_seconds": (
                float((first - event.start_at).total_seconds()) if pd.notna(first) else np.nan
            ),
        })
    return pd.DataFrame(output)
