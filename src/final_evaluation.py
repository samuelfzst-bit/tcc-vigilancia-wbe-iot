"""Congelamento do protocolo e avaliação única do holdout temporal de 2024.

Este módulo não seleciona modelos nem hiperparâmetros. Ele apenas materializa
as decisões tomadas com dados até 2023 e avalia o campeão congelado em 2024.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.modeling_v2 import (
    ModelSpec,
    baseline_predictions,
    build_estimator,
    score_predictions,
    selected_features,
)

PROTOCOL_VERSION = "avaliacao_final_v1_20261016"
EXPECTED_DATASET_VERSION = "dataset_modelagem_v1_20260927"
EXPECTED_DATASET_SHA256 = (
    "1d51c54f1d13e28b9253b6db4fa12d9538ed774da6c5d5c33b52f2cd026fcb85"
)
FINAL_MODEL = "poisson"
FINAL_CONFIG = "alpha=1"
FINAL_FEATURE_SET = "clima"
FINAL_MEMORY = "full"
FINAL_TEST_YEAR = 2024
CONFIRMATION_TOKEN = "ABRIR_2024_APENAS_PARA_TESTE_FINAL"


@dataclass(frozen=True)
class Champion:
    horizon: int
    model: str = FINAL_MODEL
    config_id: str = FINAL_CONFIG
    alpha: float = 1.0
    feature_set: str = FINAL_FEATURE_SET
    memory: str = FINAL_MEMORY


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Hash determinístico de um objeto JSON."""

    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _single_dataset_version(df: pd.DataFrame) -> str:
    values = df["versao_dataset"].dropna().astype(str).unique().tolist()
    if values != [EXPECTED_DATASET_VERSION]:
        raise ValueError(
            "Versão do dataset divergente do protocolo: " f"{values!r}"
        )
    return values[0]


def build_frozen_protocol(
    df: pd.DataFrame,
    dataset_sha256: str,
    *,
    created_at_utc: str,
    git_commit: str,
) -> dict[str, Any]:
    """Congela modelo, features e alerta usando somente dados até 2023.

    O alvo de 2024 não participa de nenhum valor produzido por esta função.
    """

    if dataset_sha256 != EXPECTED_DATASET_SHA256:
        raise ValueError("SHA-256 do dataset não corresponde ao snapshot aprovado")
    dataset_version = _single_dataset_version(df)
    years = pd.to_numeric(df["ano_alvo"], errors="raise")
    development = df.loc[years.le(2023)].copy()
    if development.empty:
        raise ValueError("Período de desenvolvimento até 2023 está vazio")

    champions: list[dict[str, Any]] = []
    for horizon in (1, 2):
        frame = development.loc[development["horizonte"].eq(horizon)].copy()
        if frame.empty:
            raise ValueError(f"Sem dados de desenvolvimento para t+{horizon}")
        features = selected_features(frame, FINAL_FEATURE_SET, FINAL_MEMORY)
        if not features:
            raise ValueError(f"Sem features congeláveis para t+{horizon}")
        q75 = float(frame["target_casos"].quantile(0.75))
        alert_threshold = int(max(1, math.ceil(q75)))
        champion = Champion(horizon)
        champions.append(
            {
                "horizonte": champion.horizon,
                "modelo": champion.model,
                "config_id": champion.config_id,
                "parametros": {"alpha": champion.alpha, "max_iter": 3000},
                "conjunto_features": champion.feature_set,
                "memoria": champion.memory,
                "features": features,
                "n_desenvolvimento": int(len(frame)),
                "periodo_treino_final": "2010-2023",
                "limiar_alerta": alert_threshold,
                "quantil_75_desenvolvimento": q75,
            }
        )

    protocol: dict[str, Any] = {
        "versao_protocolo": PROTOCOL_VERSION,
        "criado_em_utc": created_at_utc,
        "git_commit_congelamento": git_commit,
        "dataset": {
            "versao": dataset_version,
            "sha256": dataset_sha256,
            "cenario": "principal_sem_importados_conhecidos",
            "fonte_disponibilidade": "DT_ENCERRA",
        },
        "desenho_temporal": {
            "selecao_cv": "2018-2022",
            "validacao_final": 2023,
            "treino_final": "2010-2023",
            "teste_unico": FINAL_TEST_YEAR,
        },
        "metrica_primaria": "MAE",
        "campeoes": champions,
        "regra_alerta": {
            "nome": "incidencia_semanal_elevada",
            "formula": "previsao >= ceil(Q75 do alvo no desenvolvimento ate 2023)",
            "evento_observado": "casos_observados >= o mesmo limiar congelado",
            "natureza": "limiar estatistico do prototipo; nao e limiar clinico oficial",
        },
        "evidencia_decisao": {
            "execucao_modelagem_v2": "20261016T030743Z",
            "execucao_xgboost_challenger": "20261016T032859Z",
            "poisson_mae_2023": {"t+1": 1.4051259605667827, "t+2": 1.6883320029901883},
            "xgboost_mae_2023": {"t+1": 1.376881507726816, "t+2": 1.657834721299318},
            "xgboost_substitui_poisson": {"t+1": False, "t+2": False},
        },
        "restricoes": [
            "2024 nao pode alterar modelo, features, hiperparametros ou limiar",
            "resultado desfavoravel deve ser reportado, nao otimizado retroativamente",
            "qualquer experimento posterior deve ser rotulado como analise pos-hoc",
        ],
    }
    protocol["sha256_protocolo"] = canonical_sha256(protocol)
    return protocol


def validate_frozen_protocol(protocol: dict[str, Any]) -> None:
    """Valida identidade e integridade do protocolo antes de abrir 2024."""

    supplied = protocol.get("sha256_protocolo")
    copy = deepcopy(protocol)
    copy.pop("sha256_protocolo", None)
    calculated = canonical_sha256(copy)
    if supplied != calculated:
        raise ValueError("Manifesto de congelamento foi alterado após sua criação")
    if protocol.get("versao_protocolo") != PROTOCOL_VERSION:
        raise ValueError("Versão de protocolo inesperada")
    if protocol.get("dataset", {}).get("sha256") != EXPECTED_DATASET_SHA256:
        raise ValueError("Dataset do protocolo não é o snapshot aprovado")
    champions = protocol.get("campeoes", [])
    if {row.get("horizonte") for row in champions} != {1, 2}:
        raise ValueError("O protocolo deve congelar t+1 e t+2")
    for row in champions:
        if row.get("modelo") != FINAL_MODEL or row.get("config_id") != FINAL_CONFIG:
            raise ValueError("Campeão divergente da decisão pré-teste")


def classification_metrics(y_true, y_pred, threshold: float) -> dict[str, float | int]:
    """Métricas do alerta binário derivado das contagens previstas."""

    observed = np.asarray(y_true, dtype=float) >= threshold
    predicted = np.asarray(y_pred, dtype=float) >= threshold
    tp = int(np.sum(observed & predicted))
    fp = int(np.sum(~observed & predicted))
    fn = int(np.sum(observed & ~predicted))
    tn = int(np.sum(~observed & ~predicted))

    def safe_div(numerator: float, denominator: float) -> float:
        return float(numerator / denominator) if denominator else float("nan")

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = safe_div(2 * precision * recall, precision + recall)
    balanced_accuracy = float(np.nanmean([recall, specificity]))
    return {
        "limiar_alerta": float(threshold),
        "verdadeiros_positivos": tp,
        "falsos_positivos": fp,
        "falsos_negativos": fn,
        "verdadeiros_negativos": tn,
        "precisao_alerta": precision,
        "recall_alerta": recall,
        "especificidade": specificity,
        "f1_alerta": f1,
        "acuracia_balanceada": balanced_accuracy,
    }


def block_bootstrap_mae_interval(
    y_true,
    y_pred,
    *,
    block_size: int = 4,
    n_bootstrap: int = 2000,
    random_state: int = 42,
) -> tuple[float, float]:
    """IC95% descritivo do MAE por bootstrap circular em blocos semanais."""

    truth = np.asarray(y_true, dtype=float)
    prediction = np.asarray(y_pred, dtype=float)
    if len(truth) != len(prediction) or len(truth) == 0:
        raise ValueError("Séries inválidas para bootstrap")
    if block_size < 1 or block_size > len(truth):
        raise ValueError("Tamanho de bloco inválido")
    rng = np.random.default_rng(random_state)
    errors = np.abs(truth - prediction)
    values = np.empty(n_bootstrap, dtype=float)
    blocks_needed = math.ceil(len(errors) / block_size)
    offsets = np.arange(block_size)
    for index in range(n_bootstrap):
        starts = rng.integers(0, len(errors), size=blocks_needed)
        sampled = ((starts[:, None] + offsets) % len(errors)).ravel()[: len(errors)]
        values[index] = float(errors[sampled].mean())
    low, high = np.quantile(values, [0.025, 0.975])
    return float(low), float(high)


def evaluate_locked_2024(
    df: pd.DataFrame,
    protocol: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[int, Any]]:
    """Treina em 2010–2023 e avalia o protocolo congelado no holdout de 2024."""

    validate_frozen_protocol(protocol)
    champions = {row["horizonte"]: row for row in protocol["campeoes"]}
    metric_rows: list[dict[str, Any]] = []
    alert_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    fitted_models: dict[int, Any] = {}

    for horizon in (1, 2):
        frame = df.loc[df["horizonte"].eq(horizon)].copy()
        frame_years = pd.to_numeric(frame["ano_alvo"], errors="raise")
        development = frame.loc[frame_years.le(2023)].sort_values("inicio_semana_t")
        test = frame.loc[frame_years.eq(FINAL_TEST_YEAR)].sort_values(
            "inicio_semana_alvo"
        )
        if development.empty or test.empty:
            raise ValueError(f"Treino final ou teste vazio para t+{horizon}")
        if int(pd.to_numeric(development["ano_alvo"]).max()) >= FINAL_TEST_YEAR:
            raise AssertionError("Treino final contém o ano de teste")

        frozen = champions[horizon]
        features = list(frozen["features"])
        missing = sorted(set(features) - set(frame.columns))
        if missing:
            raise ValueError(f"Features congeladas ausentes: {missing}")
        current_features = selected_features(frame, FINAL_FEATURE_SET, FINAL_MEMORY)
        if features != current_features:
            raise ValueError("Lista de features divergiu após o congelamento")

        estimator = build_estimator(
            ModelSpec(FINAL_MODEL, FINAL_CONFIG, {"alpha": 1.0})
        )
        estimator.fit(development[features], development["target_casos"])
        prediction = np.clip(estimator.predict(test[features]), 1e-9, None)
        fitted_models[horizon] = estimator
        threshold = float(frozen["limiar_alerta"])

        candidates: dict[str, np.ndarray | pd.Series] = {
            "poisson_final": prediction,
            **baseline_predictions(development, test),
        }
        for model_name, candidate_prediction in candidates.items():
            series = pd.Series(candidate_prediction, index=test.index, dtype=float)
            valid = series.notna()
            truth = test.loc[valid, "target_casos"].to_numpy(dtype=float)
            pred = np.clip(series.loc[valid].to_numpy(dtype=float), 1e-9, None)
            metrics = score_predictions(truth, pred, threshold)
            ci_low, ci_high = block_bootstrap_mae_interval(
                truth, pred, random_state=42 + horizon
            )
            observed_mean = float(np.mean(truth))
            predicted_mean = float(np.mean(pred))
            metric_rows.append(
                {
                    "horizonte": horizon,
                    "modelo": model_name,
                    "split": "teste_2024",
                    "modelo_congelado": model_name == "poisson_final",
                    **metrics,
                    "mae_ic95_inferior": ci_low,
                    "mae_ic95_superior": ci_high,
                    "media_observada": observed_mean,
                    "media_prevista": predicted_mean,
                    "razao_calibracao": (
                        predicted_mean / observed_mean if observed_mean else float("nan")
                    ),
                }
            )

        alert_rows.append(
            {
                "horizonte": horizon,
                "modelo": "poisson_final",
                "split": "teste_2024",
                **classification_metrics(
                    test["target_casos"].to_numpy(dtype=float), prediction, threshold
                ),
            }
        )
        for date, truth, pred in zip(
            test["inicio_semana_alvo"], test["target_casos"], prediction
        ):
            prediction_rows.append(
                {
                    "horizonte": horizon,
                    "inicio_semana_alvo": date,
                    "observado": float(truth),
                    "previsto": float(pred),
                    "erro": float(pred - truth),
                    "erro_absoluto": float(abs(pred - truth)),
                    "limiar_alerta": threshold,
                    "alerta_observado": bool(float(truth) >= threshold),
                    "alerta_previsto": bool(float(pred) >= threshold),
                }
            )

    return (
        pd.DataFrame(metric_rows),
        pd.DataFrame(alert_rows),
        pd.DataFrame(prediction_rows),
        fitted_models,
    )
