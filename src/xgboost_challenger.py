"""Challenger XGBoost pré-especificado para a modelagem epidemiológica.

O protocolo compara XGBoost e Poisson com exatamente as mesmas features,
folds e datas. O teste de 2024 nunca é acessado por este módulo.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.modeling_v2 import (
    CV_YEARS,
    RANDOM_STATE,
    ModelSpec,
    build_estimator,
    expanding_folds,
    score_predictions,
    selected_features,
)

MIN_MAE_IMPROVEMENT = 0.05
MAX_CV_SD_RATIO = 1.25
MAX_PEAK_MAE_RATIO = 1.10


@dataclass(frozen=True)
class XGBoostSpec:
    config_id: str
    n_estimators: int
    max_depth: int
    learning_rate: float


def xgboost_specs() -> list[XGBoostSpec]:
    """Grade pequena definida antes de consultar a validação de 2023."""

    return [
        XGBoostSpec(
            config_id=f"trees={trees}|depth={depth}|lr={learning_rate:g}",
            n_estimators=trees,
            max_depth=depth,
            learning_rate=learning_rate,
        )
        for trees in (200, 400)
        for depth in (2, 3)
        for learning_rate in (0.03, 0.05)
    ]


def build_xgboost(spec: XGBoostSpec):
    """Constrói o estimador com objetivo de contagem e regularização fixa."""

    from xgboost import XGBRegressor

    return XGBRegressor(
        objective="count:poisson",
        eval_metric="mae",
        n_estimators=spec.n_estimators,
        max_depth=spec.max_depth,
        learning_rate=spec.learning_rate,
        min_child_weight=5.0,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.0,
        reg_lambda=10.0,
        tree_method="hist",
        n_jobs=2,
        random_state=RANDOM_STATE,
    )


def _fold_row(
    horizon: int,
    model: str,
    config_id: str,
    year: int,
    metrics: dict[str, float | int],
) -> dict[str, float | int | str]:
    return {
        "horizonte": horizon,
        "modelo": model,
        "config_id": config_id,
        "ano_validacao": year,
        **metrics,
    }


def run_challenger_cv(
    df: pd.DataFrame,
    specs: Iterable[XGBoostSpec] | None = None,
    validation_years: Iterable[int] = CV_YEARS,
) -> pd.DataFrame:
    """Compara XGBoost e o Poisson congelado apenas até 2022."""

    specs = list(specs or xgboost_specs())
    poisson_spec = ModelSpec("poisson", "alpha=1", {"alpha": 1.0})
    rows: list[dict] = []
    development = df.loc[pd.to_numeric(df["ano_alvo"]).le(2022)].copy()

    for horizon in (1, 2):
        frame = development.loc[development["horizonte"].eq(horizon)].copy()
        features = selected_features(frame, "clima", memory="full")
        for year, train, validation in expanding_folds(frame, validation_years):
            threshold = float(train["target_casos"].quantile(0.75))

            poisson = build_estimator(poisson_spec)
            poisson.fit(train[features], train["target_casos"])
            metrics = score_predictions(
                validation["target_casos"], poisson.predict(validation[features]), threshold
            )
            rows.append(_fold_row(horizon, "poisson", "alpha=1", year, metrics))

            for spec in specs:
                model = build_xgboost(spec)
                model.fit(train[features], train["target_casos"])
                metrics = score_predictions(
                    validation["target_casos"], model.predict(validation[features]), threshold
                )
                rows.append(
                    _fold_row(horizon, "xgboost_poisson", spec.config_id, year, metrics)
                )
    return pd.DataFrame(rows)


def summarize_challenger_cv(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    keys = ["horizonte", "modelo", "config_id"]
    return (
        fold_metrics.groupby(keys, observed=True)
        .agg(
            folds=("ano_validacao", "nunique"),
            mae_media=("mae", "mean"),
            mae_desvio=("mae", "std"),
            mae_pior_fold=("mae", "max"),
            rmse_medio=("rmse", "mean"),
            bias_medio=("bias", "mean"),
            mae_picos_media=("mae_picos", "mean"),
        )
        .reset_index()
        .sort_values(["horizonte", "mae_media", "rmse_medio", "mae_desvio"])
        .reset_index(drop=True)
    )


def select_xgboost_configs(cv_summary: pd.DataFrame) -> pd.DataFrame:
    """Seleciona um XGBoost por horizonte sem olhar 2023."""

    candidates = cv_summary.loc[cv_summary["modelo"].eq("xgboost_poisson")].copy()
    return (
        candidates.sort_values(
            ["horizonte", "mae_media", "rmse_medio", "mae_desvio"]
        )
        .groupby("horizonte", as_index=False, observed=True)
        .head(1)
        .reset_index(drop=True)
    )


def evaluate_challenger_2023(
    df: pd.DataFrame,
    selected_xgboost: pd.DataFrame,
    specs: Iterable[XGBoostSpec] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Avalia Poisson congelado e XGBoost selecionado na validação de 2023."""

    specs = list(specs or xgboost_specs())
    lookup = {spec.config_id: spec for spec in specs}
    poisson_spec = ModelSpec("poisson", "alpha=1", {"alpha": 1.0})
    metric_rows: list[dict] = []
    prediction_rows: list[dict] = []

    for horizon in (1, 2):
        frame = df.loc[df["horizonte"].eq(horizon)].copy()
        train = frame.loc[pd.to_numeric(frame["ano_alvo"]).le(2022)]
        validation = frame.loc[pd.to_numeric(frame["ano_alvo"]).eq(2023)].sort_values(
            "inicio_semana_alvo"
        )
        features = selected_features(frame, "clima", memory="full")
        threshold = float(train["target_casos"].quantile(0.75))
        xgb_config = selected_xgboost.loc[
            selected_xgboost["horizonte"].eq(horizon), "config_id"
        ].iloc[0]
        candidates = (
            ("poisson", "alpha=1", build_estimator(poisson_spec)),
            ("xgboost_poisson", xgb_config, build_xgboost(lookup[xgb_config])),
        )

        for model_name, config_id, model in candidates:
            model.fit(train[features], train["target_casos"])
            prediction = np.clip(model.predict(validation[features]), 1e-9, None)
            metrics = score_predictions(
                validation["target_casos"], prediction, threshold
            )
            metric_rows.append(
                {
                    "horizonte": horizon,
                    "modelo": model_name,
                    "config_id": config_id,
                    "split": "validacao_2023",
                    **metrics,
                }
            )
            for date, truth, pred in zip(
                validation["inicio_semana_alvo"],
                validation["target_casos"],
                prediction,
            ):
                prediction_rows.append(
                    {
                        "horizonte": horizon,
                        "inicio_semana_alvo": date,
                        "modelo": model_name,
                        "config_id": config_id,
                        "observado": float(truth),
                        "previsto": float(pred),
                        "erro": float(pred - truth),
                    }
                )
    return pd.DataFrame(metric_rows), pd.DataFrame(prediction_rows)


def decide_challenger(
    validation: pd.DataFrame,
    cv_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Aplica a regra pré-registrada sem qualquer consulta ao teste de 2024."""

    outputs: list[dict] = []
    for horizon in (1, 2):
        val_h = validation.loc[validation["horizonte"].eq(horizon)]
        cv_h = cv_summary.loc[cv_summary["horizonte"].eq(horizon)]
        poisson_val = val_h.loc[val_h["modelo"].eq("poisson")].iloc[0]
        xgb_val = val_h.loc[val_h["modelo"].eq("xgboost_poisson")].iloc[0]
        poisson_cv = cv_h.loc[cv_h["modelo"].eq("poisson")].iloc[0]
        xgb_cv = cv_h.loc[
            cv_h["modelo"].eq("xgboost_poisson")
            & cv_h["config_id"].eq(xgb_val["config_id"])
        ].iloc[0]

        improvement = (poisson_val["mae"] - xgb_val["mae"]) / poisson_val["mae"]
        checks = {
            "melhora_mae_5pct": improvement >= MIN_MAE_IMPROVEMENT,
            "cv_medio_nao_piora": xgb_cv["mae_media"] <= poisson_cv["mae_media"],
            "estabilidade_aceitavel": xgb_cv["mae_desvio"]
            <= poisson_cv["mae_desvio"] * MAX_CV_SD_RATIO,
            "picos_aceitaveis": xgb_val["mae_picos"]
            <= poisson_val["mae_picos"] * MAX_PEAK_MAE_RATIO,
        }
        replace = all(checks.values())
        outputs.append(
            {
                "horizonte": horizon,
                "poisson_mae_2023": poisson_val["mae"],
                "xgboost_mae_2023": xgb_val["mae"],
                "melhora_relativa_mae": improvement,
                **checks,
                "modelo_recomendado": "xgboost_poisson" if replace else "poisson",
                "xgboost_substitui_poisson": replace,
            }
        )
    return pd.DataFrame(outputs)
