"""Analises pos-hoc do teste final de 2024.

Este modulo nao seleciona nem altera o modelo congelado. Ele transforma os
artefatos finais em diagnosticos de erro, sensibilidade descritiva de limiares
e interpretacao dos coeficientes padronizados do Poisson.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd

from src.final_evaluation import classification_metrics

OFFICIAL_ALERT_THRESHOLD = 4.0
EXPLORATORY_ATTENTION_THRESHOLD = 2.0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_final_run(run_dir: Path) -> dict[str, Any]:
    """Confere a integridade dos arquivos registrados no manifesto final."""

    manifest_path = run_dir / "manifest_final.json"
    if not manifest_path.exists():
        raise FileNotFoundError("manifest_final.json nao encontrado")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("model_change_after_test_allowed") is not False:
        raise ValueError("Manifesto nao bloqueia alteracao pos-teste do modelo")
    if manifest.get("test_opened_once") is not True:
        raise ValueError("Manifesto nao registra abertura unica do teste")

    divergences: list[str] = []
    for filename, expected_hash in manifest.get("files", {}).items():
        path = run_dir / filename
        if not path.exists():
            divergences.append(f"ausente: {filename}")
        elif file_sha256(path) != expected_hash:
            divergences.append(f"hash divergente: {filename}")
    if divergences:
        raise ValueError("Execucao final invalida: " + "; ".join(divergences))
    return manifest


def threshold_sensitivity(
    predictions: pd.DataFrame,
    thresholds: Iterable[float] = (2.0, 3.0, 4.0, 5.0),
) -> pd.DataFrame:
    """Compara cortes alternativos sem substituir o limiar oficial."""

    rows: list[dict[str, Any]] = []
    for horizon, frame in predictions.groupby("horizonte", observed=True):
        truth = frame["observado"].to_numpy(dtype=float)
        predicted = frame["previsto"].to_numpy(dtype=float)
        for threshold in thresholds:
            metrics = classification_metrics(truth, predicted, float(threshold))
            observed_alerts = int(np.sum(truth >= threshold))
            predicted_alerts = int(np.sum(predicted >= threshold))
            rows.append(
                {
                    "horizonte": int(horizon),
                    **metrics,
                    "semanas": int(len(frame)),
                    "alertas_observados": observed_alerts,
                    "alertas_previstos": predicted_alerts,
                    "taxa_alerta_observada": observed_alerts / len(frame),
                    "taxa_alerta_prevista": predicted_alerts / len(frame),
                    "status_metodologico": (
                        "oficial_congelado"
                        if float(threshold) == OFFICIAL_ALERT_THRESHOLD
                        else "exploratorio_pos_hoc"
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["horizonte", "limiar_alerta"]
    ).reset_index(drop=True)


def weekly_error_audit(predictions: pd.DataFrame) -> pd.DataFrame:
    """Classifica os erros semanais usando apenas o limiar oficial congelado."""

    frame = predictions.copy()
    frame["inicio_semana_alvo"] = pd.to_datetime(frame["inicio_semana_alvo"])
    observed = frame["observado"].ge(OFFICIAL_ALERT_THRESHOLD)
    predicted = frame["previsto"].ge(OFFICIAL_ALERT_THRESHOLD)
    frame["tipo_alerta"] = np.select(
        [observed & predicted, ~observed & predicted, observed & ~predicted],
        ["verdadeiro_positivo", "falso_positivo", "falso_negativo"],
        default="verdadeiro_negativo",
    )
    frame["direcao_erro"] = np.select(
        [frame["erro"].gt(0), frame["erro"].lt(0)],
        ["superestimacao", "subestimacao"],
        default="sem_erro",
    )
    frame["mes"] = frame["inicio_semana_alvo"].dt.to_period("M").astype(str)
    frame["ranking_erro_absoluto"] = (
        frame.groupby("horizonte", observed=True)["erro_absoluto"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return frame.sort_values(
        ["horizonte", "ranking_erro_absoluto"]
    ).reset_index(drop=True)


def monthly_error_summary(audit: pd.DataFrame) -> pd.DataFrame:
    """Resume concentracao temporal, viés e alertas por mes."""

    frame = audit.copy()
    frame["observado_alerta"] = frame["observado"].ge(OFFICIAL_ALERT_THRESHOLD)
    frame["previsto_alerta"] = frame["previsto"].ge(OFFICIAL_ALERT_THRESHOLD)
    return (
        frame.groupby(["horizonte", "mes"], observed=True)
        .agg(
            semanas=("observado", "size"),
            casos_observados=("observado", "sum"),
            casos_previstos=("previsto", "sum"),
            mae=("erro_absoluto", "mean"),
            bias=("erro", "mean"),
            alertas_observados=("observado_alerta", "sum"),
            alertas_previstos=("previsto_alerta", "sum"),
        )
        .reset_index()
    )


def poisson_coefficients(model_path: Path, horizon: int) -> pd.DataFrame:
    """Extrai efeitos por 1 desvio-padrao do pipeline Poisson salvo."""

    model = joblib.load(model_path)
    if not hasattr(model, "named_steps"):
        raise TypeError("Artefato nao e um Pipeline do scikit-learn")
    imputer = model.named_steps["simpleimputer"]
    regressor = model.named_steps["poissonregressor"]
    names = np.asarray(imputer.get_feature_names_out(), dtype=str)
    coefficients = np.asarray(regressor.coef_, dtype=float)
    if len(names) != len(coefficients):
        raise ValueError("Numero de coeficientes diverge das features transformadas")

    frame = pd.DataFrame(
        {
            "horizonte": int(horizon),
            "feature_transformada": names,
            "coeficiente_log_padronizado": coefficients,
        }
    )
    frame["razao_taxa_por_1dp"] = np.exp(frame["coeficiente_log_padronizado"])
    frame["variacao_percentual_por_1dp"] = (
        frame["razao_taxa_por_1dp"] - 1.0
    ) * 100.0
    frame["modulo_coeficiente"] = frame["coeficiente_log_padronizado"].abs()
    frame["tipo_feature"] = np.where(
        frame["feature_transformada"].str.startswith("missingindicator_"),
        "indicador_ausencia",
        "valor",
    )
    frame["ranking_modulo"] = (
        frame["modulo_coeficiente"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return frame.sort_values("ranking_modulo").reset_index(drop=True)


def dashboard_predictions(
    predictions: pd.DataFrame,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    execution_id: str,
) -> pd.DataFrame:
    """Prepara o contrato de dados para a futura tabela do dashboard."""

    frame = predictions.copy()
    frame["inicio_semana_alvo"] = pd.to_datetime(
        frame["inicio_semana_alvo"]
    ).dt.date
    frame["nivel_previsto"] = np.select(
        [
            frame["previsto"].ge(OFFICIAL_ALERT_THRESHOLD),
            frame["previsto"].ge(EXPLORATORY_ATTENTION_THRESHOLD),
        ],
        ["alerta", "atencao"],
        default="normal",
    )
    frame["limiar_atencao"] = EXPLORATORY_ATTENTION_THRESHOLD
    frame["limiar_alerta"] = OFFICIAL_ALERT_THRESHOLD
    frame["modelo"] = "poisson"
    frame["versao_modelo"] = protocol["versao_protocolo"]
    frame["execucao_id"] = execution_id
    frame["git_commit"] = manifest["git_commit"]
    frame["analise_pos_hoc"] = False
    columns = [
        "inicio_semana_alvo",
        "horizonte",
        "observado",
        "previsto",
        "nivel_previsto",
        "limiar_atencao",
        "limiar_alerta",
        "alerta_observado",
        "alerta_previsto",
        "erro",
        "erro_absoluto",
        "modelo",
        "versao_modelo",
        "execucao_id",
        "git_commit",
        "analise_pos_hoc",
    ]
    return frame[columns].sort_values(
        ["inicio_semana_alvo", "horizonte"]
    ).reset_index(drop=True)
