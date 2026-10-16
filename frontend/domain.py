"""Regras de apresentacao independentes do Streamlit."""

from __future__ import annotations


def prediction_level(value: float, attention: float = 2.0, alert: float = 4.0) -> str:
    if value >= alert:
        return "alerta"
    if value >= attention:
        return "atencao"
    return "normal"


def level_label(level: str) -> str:
    labels = {
        "normal": "Normal",
        "atencao": "Atenção",
        "alerta": "Alerta",
    }
    if level not in labels:
        raise ValueError(f"Nivel desconhecido: {level}")
    return labels[level]
