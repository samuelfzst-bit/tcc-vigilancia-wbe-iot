"""Treino temporal, baselines e avaliação para contagens semanais."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error, mean_poisson_deviance, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


NON_FEATURE_COLUMNS = {
    "horizonte", "inicio_semana_t", "data_corte", "inicio_semana_alvo",
    "ano_alvo", "semana_alvo", "target_casos", "split",
    "cenario_geografico", "fonte_disponibilidade",
    "versao_base_epidemiologica", "versao_dataset",
}


@dataclass(frozen=True)
class Result:
    horizonte: int
    conjunto: str
    modelo: str
    split: str
    n: int
    mae: float
    rmse: float
    poisson_deviance: float


def feature_columns(df: pd.DataFrame, feature_set: str) -> list[str]:
    candidates = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    epi = [c for c in candidates if "conhecid" in c]
    climate_tokens = ("precipit", "temperatura", "umidade", "vento", "clima_")
    climate = [c for c in candidates if any(token in c for token in climate_tokens)]
    seasonal = [c for c in candidates if c in {"semana_alvo_sin", "semana_alvo_cos"}]
    mapping = {
        "epidemiologia": epi + seasonal,
        "clima": climate + seasonal,
        "combinado": epi + climate + seasonal,
    }
    if feature_set not in mapping:
        raise ValueError(f"Conjunto desconhecido: {feature_set}")
    return list(dict.fromkeys(mapping[feature_set]))


def candidate_models(random_state: int = 42):
    return {
        "poisson": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            PoissonRegressor(alpha=1.0, max_iter=2_000),
        ),
        "hist_gradient_boosting_poisson": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=False),
            HistGradientBoostingRegressor(
                loss="poisson", learning_rate=0.05, max_iter=300,
                l2_regularization=1.0, random_state=random_state,
            ),
        ),
        "random_forest_poisson": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RandomForestRegressor(
                n_estimators=500, criterion="poisson", min_samples_leaf=4,
                max_features=0.8, n_jobs=-1, random_state=random_state,
            ),
        ),
    }


def score(y_true, y_pred) -> dict[str, float]:
    prediction = np.clip(np.asarray(y_pred, dtype=float), 1e-9, None)
    truth = np.asarray(y_true, dtype=float)
    return {
        "mae": mean_absolute_error(truth, prediction),
        "rmse": mean_squared_error(truth, prediction) ** 0.5,
        "poisson_deviance": mean_poisson_deviance(truth, prediction),
    }


def baseline_predictions(frame: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "baseline_lag_2": frame["casos_conhecidos_lag_2"],
        "baseline_media_lags_2_5": frame["media_conhecida_lags_2_5"],
        "baseline_sazonal_lag_52": frame["casos_conhecidos_lag_52"],
    }


def fit_and_validate(df: pd.DataFrame, horizonte: int, feature_set: str):
    frame = df.loc[df["horizonte"].eq(horizonte)].sort_values("inicio_semana_t")
    train = frame.loc[frame["split"].eq("treino")]
    validation = frame.loc[frame["split"].eq("validacao")]
    features = feature_columns(frame, feature_set)
    if not features:
        raise ValueError(f"Nenhuma feature para {feature_set}")

    rows = []
    fitted = {}
    for name, pred in baseline_predictions(validation).items():
        valid = pred.notna()
        metrics = score(validation.loc[valid, "target_casos"], pred.loc[valid])
        rows.append(Result(horizonte, feature_set, name, "validacao", int(valid.sum()), **metrics))

    for name, estimator in candidate_models().items():
        model = clone(estimator)
        model.fit(train[features], train["target_casos"])
        metrics = score(validation["target_casos"], model.predict(validation[features]))
        rows.append(Result(horizonte, feature_set, name, "validacao", len(validation), **metrics))
        fitted[name] = model
    return pd.DataFrame([r.__dict__ for r in rows]), fitted, features


def evaluate_locked_test(df, horizonte, feature_set, model_name, model, features):
    """Refaz o ajuste em treino+validação e abre 2024 somente após congelamento."""
    frame = df.loc[df["horizonte"].eq(horizonte)].sort_values("inicio_semana_t")
    development = frame.loc[frame["split"].isin(["treino", "validacao"])]
    test = frame.loc[frame["split"].eq("teste")]
    final_model = clone(model).fit(development[features], development["target_casos"])
    metrics = score(test["target_casos"], final_model.predict(test[features]))
    result = Result(horizonte, feature_set, model_name, "teste", len(test), **metrics)
    return final_model, result
