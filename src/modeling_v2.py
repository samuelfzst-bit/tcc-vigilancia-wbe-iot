"""Validação temporal robusta para a previsão semanal de leptospirose.

O módulo mantém 2024 fora de qualquer seleção. Hiperparâmetros são escolhidos
em folds expansivos de 2018 a 2022 e 2023 é usado como validação final.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor, TweedieRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_poisson_deviance,
    mean_squared_error,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.modeling import NON_FEATURE_COLUMNS, feature_columns

RANDOM_STATE = 42
CV_YEARS = (2018, 2019, 2020, 2021, 2022)
LONG_MEMORY_TOKENS = ("lag_8", "lag_12", "lag_52", "acum_8s", "media_8s")


@dataclass(frozen=True)
class ModelSpec:
    model: str
    config_id: str
    params: dict[str, float | int | str | None]


def model_specs() -> list[ModelSpec]:
    """Grade pequena e auditável, adequada ao tempo disponível no Colab."""

    specs: list[ModelSpec] = []
    for alpha in (0.01, 0.1, 1.0, 10.0):
        specs.append(ModelSpec("poisson", f"alpha={alpha:g}", {"alpha": alpha}))
    for power in (1.1, 1.5, 1.9):
        for alpha in (0.1, 1.0):
            specs.append(
                ModelSpec(
                    "tweedie",
                    f"power={power:g}|alpha={alpha:g}",
                    {"power": power, "alpha": alpha},
                )
            )
    for leaf, features in ((2, 0.6), (4, 0.8), (8, 0.8), (4, 1.0)):
        specs.append(
            ModelSpec(
                "random_forest_poisson",
                f"leaf={leaf}|features={features:g}",
                {"min_samples_leaf": leaf, "max_features": features},
            )
        )
    for leaf, l2 in ((10, 1.0), (20, 1.0), (10, 10.0), (20, 10.0)):
        specs.append(
            ModelSpec(
                "hist_gradient_boosting_poisson",
                f"leaf={leaf}|l2={l2:g}",
                {"min_samples_leaf": leaf, "l2_regularization": l2},
            )
        )
    return specs


def build_estimator(spec: ModelSpec):
    """Cria um estimador novo; nenhum estado é compartilhado entre folds."""

    if spec.model == "poisson":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            PoissonRegressor(alpha=float(spec.params["alpha"]), max_iter=3_000),
        )
    if spec.model == "tweedie":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            TweedieRegressor(
                power=float(spec.params["power"]),
                alpha=float(spec.params["alpha"]),
                link="log",
                max_iter=3_000,
            ),
        )
    if spec.model == "random_forest_poisson":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RandomForestRegressor(
                n_estimators=300,
                criterion="poisson",
                min_samples_leaf=int(spec.params["min_samples_leaf"]),
                max_features=float(spec.params["max_features"]),
                n_jobs=-1,
                random_state=RANDOM_STATE,
            ),
        )
    if spec.model == "hist_gradient_boosting_poisson":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=False),
            HistGradientBoostingRegressor(
                loss="poisson",
                learning_rate=0.05,
                max_iter=300,
                min_samples_leaf=int(spec.params["min_samples_leaf"]),
                l2_regularization=float(spec.params["l2_regularization"]),
                random_state=RANDOM_STATE,
            ),
        )
    raise ValueError(f"Modelo desconhecido: {spec.model}")


def selected_features(
    df: pd.DataFrame,
    feature_set: str,
    memory: str = "full",
) -> list[str]:
    features = feature_columns(df, feature_set)
    if memory == "short":
        features = [
            c for c in features if not any(token in c for token in LONG_MEMORY_TOKENS)
        ]
    elif memory != "full":
        raise ValueError(f"Memória desconhecida: {memory}")
    return features


def expanding_folds(
    frame: pd.DataFrame,
    validation_years: Iterable[int] = CV_YEARS,
    min_train_year: int | None = None,
):
    """Gera treino passado -> ano seguinte, sem embaralhamento."""

    years = pd.to_numeric(frame["ano_alvo"])
    for validation_year in validation_years:
        train_mask = years.lt(validation_year)
        if min_train_year is not None:
            train_mask &= years.ge(min_train_year)
        train = frame.loc[train_mask].sort_values("inicio_semana_t")
        validation = frame.loc[years.eq(validation_year)].sort_values("inicio_semana_t")
        if train.empty or validation.empty:
            raise ValueError(f"Fold {validation_year} sem treino ou validação")
        if pd.to_numeric(train["ano_alvo"]).max() >= validation_year:
            raise AssertionError("Fold temporal contém observação futura no treino")
        yield validation_year, train, validation


def score_predictions(
    y_true,
    y_pred,
    peak_threshold: float,
) -> dict[str, float | int]:
    truth = np.asarray(y_true, dtype=float)
    prediction = np.clip(np.asarray(y_pred, dtype=float), 1e-9, None)
    peak_mask = truth >= peak_threshold
    peak_mae = (
        mean_absolute_error(truth[peak_mask], prediction[peak_mask])
        if peak_mask.any()
        else np.nan
    )
    return {
        "n": len(truth),
        "mae": float(mean_absolute_error(truth, prediction)),
        "rmse": float(mean_squared_error(truth, prediction) ** 0.5),
        "poisson_deviance": float(mean_poisson_deviance(truth, prediction)),
        "bias": float(np.mean(prediction - truth)),
        "peak_threshold": float(peak_threshold),
        "n_picos": int(peak_mask.sum()),
        "mae_picos": float(peak_mae),
    }


def baseline_predictions(
    train: pd.DataFrame, validation: pd.DataFrame
) -> dict[str, pd.Series]:
    overall_mean = float(train["target_casos"].mean())
    seasonal = train.groupby("semana_alvo", observed=True)["target_casos"].mean()
    seasonal_prediction = validation["semana_alvo"].map(seasonal).fillna(overall_mean)
    return {
        "baseline_lag_2": validation["casos_conhecidos_lag_2"],
        "baseline_media_lags_2_5": validation["media_conhecida_lags_2_5"],
        "baseline_sazonal_lag_52": validation["casos_conhecidos_lag_52"],
        "baseline_media_historica_semana": seasonal_prediction,
    }


def run_temporal_cv(
    df: pd.DataFrame,
    specs: Iterable[ModelSpec] | None = None,
    validation_years: Iterable[int] = CV_YEARS,
    min_train_year: int | None = None,
    memory: str = "full",
) -> pd.DataFrame:
    """Executa todos os candidatos sem tocar em validação 2023 ou teste 2024."""

    specs = list(specs or model_specs())
    rows: list[dict] = []
    development = df.loc[pd.to_numeric(df["ano_alvo"]).le(2022)].copy()
    for horizon in (1, 2):
        frame = development.loc[development["horizonte"].eq(horizon)].copy()
        for year, train, validation in expanding_folds(
            frame, validation_years, min_train_year
        ):
            peak_threshold = float(train["target_casos"].quantile(0.75))
            for name, prediction in baseline_predictions(train, validation).items():
                valid = prediction.notna()
                metrics = score_predictions(
                    validation.loc[valid, "target_casos"],
                    prediction.loc[valid],
                    peak_threshold,
                )
                rows.append(
                    {
                        "horizonte": horizon,
                        "conjunto": "baseline",
                        "memoria": memory,
                        "modelo": name,
                        "config_id": "baseline",
                        "ano_validacao": year,
                        "inicio_treino": int(pd.to_numeric(train["ano_alvo"]).min()),
                        **metrics,
                    }
                )
            for feature_set in ("epidemiologia", "clima", "combinado"):
                features = selected_features(frame, feature_set, memory)
                for spec in specs:
                    model = build_estimator(spec)
                    model.fit(train[features], train["target_casos"])
                    prediction = model.predict(validation[features])
                    metrics = score_predictions(
                        validation["target_casos"], prediction, peak_threshold
                    )
                    rows.append(
                        {
                            "horizonte": horizon,
                            "conjunto": feature_set,
                            "memoria": memory,
                            "modelo": spec.model,
                            "config_id": spec.config_id,
                            "ano_validacao": year,
                            "inicio_treino": int(
                                pd.to_numeric(train["ano_alvo"]).min()
                            ),
                            **metrics,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_cv(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    keys = ["horizonte", "conjunto", "memoria", "modelo", "config_id"]
    summary = (
        fold_metrics.groupby(keys, observed=True)
        .agg(
            folds=("ano_validacao", "nunique"),
            mae_media=("mae", "mean"),
            mae_desvio=("mae", "std"),
            mae_pior_fold=("mae", "max"),
            rmse_medio=("rmse", "mean"),
            deviance_media=("poisson_deviance", "mean"),
            bias_medio=("bias", "mean"),
            mae_picos_media=("mae_picos", "mean"),
        )
        .reset_index()
    )
    return summary.sort_values(
        ["horizonte", "mae_media", "rmse_medio", "mae_desvio"],
        na_position="last",
    ).reset_index(drop=True)


def best_configs(cv_summary: pd.DataFrame) -> pd.DataFrame:
    """Seleciona hiperparâmetros por CV para cada família e conjunto."""

    candidates = cv_summary.loc[~cv_summary["modelo"].str.startswith("baseline")].copy()
    candidates = candidates.sort_values(
        ["horizonte", "conjunto", "modelo", "mae_media", "rmse_medio", "mae_desvio"]
    )
    return (
        candidates.groupby(
            ["horizonte", "conjunto", "modelo"], observed=True, as_index=False
        )
        .head(1)
        .reset_index(drop=True)
    )


def _spec_lookup(specs: Iterable[ModelSpec]) -> dict[tuple[str, str], ModelSpec]:
    return {(spec.model, spec.config_id): spec for spec in specs}


def evaluate_validation_2023(
    df: pd.DataFrame,
    selected: pd.DataFrame,
    specs: Iterable[ModelSpec] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Avalia em 2023 somente configurações escolhidas nos folds 2018–2022."""

    specs = list(specs or model_specs())
    lookup = _spec_lookup(specs)
    metric_rows: list[dict] = []
    prediction_rows: list[dict] = []
    for horizon in (1, 2):
        frame = df.loc[df["horizonte"].eq(horizon)].copy()
        train = frame.loc[pd.to_numeric(frame["ano_alvo"]).le(2022)].sort_values(
            "inicio_semana_t"
        )
        validation = frame.loc[pd.to_numeric(frame["ano_alvo"]).eq(2023)].sort_values(
            "inicio_semana_t"
        )
        peak_threshold = float(train["target_casos"].quantile(0.75))

        for name, prediction in baseline_predictions(train, validation).items():
            valid = prediction.notna()
            metrics = score_predictions(
                validation.loc[valid, "target_casos"],
                prediction.loc[valid],
                peak_threshold,
            )
            metric_rows.append(
                {
                    "horizonte": horizon,
                    "conjunto": "baseline",
                    "modelo": name,
                    "config_id": "baseline",
                    "split": "validacao_2023",
                    **metrics,
                }
            )

        chosen = selected.loc[selected["horizonte"].eq(horizon)]
        for row in chosen.itertuples(index=False):
            spec = lookup[(row.modelo, row.config_id)]
            features = selected_features(frame, row.conjunto, row.memoria)
            model = clone(build_estimator(spec))
            model.fit(train[features], train["target_casos"])
            prediction = np.clip(model.predict(validation[features]), 1e-9, None)
            metrics = score_predictions(
                validation["target_casos"], prediction, peak_threshold
            )
            metric_rows.append(
                {
                    "horizonte": horizon,
                    "conjunto": row.conjunto,
                    "modelo": row.modelo,
                    "config_id": row.config_id,
                    "split": "validacao_2023",
                    **metrics,
                }
            )
            for date, truth, pred in zip(
                validation["inicio_semana_alvo"], validation["target_casos"], prediction
            ):
                prediction_rows.append(
                    {
                        "horizonte": horizon,
                        "inicio_semana_alvo": date,
                        "conjunto": row.conjunto,
                        "modelo": row.modelo,
                        "config_id": row.config_id,
                        "observado": float(truth),
                        "previsto": float(pred),
                        "erro": float(pred - truth),
                    }
                )
    metrics = pd.DataFrame(metric_rows).sort_values(["horizonte", "mae", "rmse"])
    return metrics.reset_index(drop=True), pd.DataFrame(prediction_rows)


def rank_finalists(validation: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    """Une validação final e estabilidade do CV, sem usar o teste."""

    models = validation.loc[~validation["modelo"].str.startswith("baseline")].copy()
    cv_columns = [
        "horizonte",
        "conjunto",
        "modelo",
        "config_id",
        "mae_media",
        "mae_desvio",
        "mae_pior_fold",
        "rmse_medio",
        "mae_picos_media",
    ]
    ranked = models.merge(
        selected[cv_columns], on=["horizonte", "conjunto", "modelo", "config_id"]
    )
    ranked = ranked.sort_values(
        ["horizonte", "mae", "mae_media", "rmse", "mae_desvio"],
        na_position="last",
    )
    ranked["ranking_horizonte"] = ranked.groupby("horizonte").cumcount() + 1
    return ranked.reset_index(drop=True)


def sensitivity_candidates(finalists: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    return finalists.loc[finalists["ranking_horizonte"].le(top_n)].copy()


def run_sensitivity(
    df: pd.DataFrame,
    finalists: pd.DataFrame,
    specs: Iterable[ModelSpec] | None = None,
) -> pd.DataFrame:
    """Reavalia os finalistas com histórico estável e memória curta."""

    specs = list(specs or model_specs())
    lookup = _spec_lookup(specs)
    scenarios = (
        ("historico_completo", None, "full"),
        ("clima_estavel_desde_2015", 2015, "full"),
        ("sem_janelas_longas", None, "short"),
    )
    outputs: list[pd.DataFrame] = []
    for scenario, start_year, memory in scenarios:
        for candidate in finalists.itertuples(index=False):
            spec = lookup[(candidate.modelo, candidate.config_id)]
            frame = df.loc[
                pd.to_numeric(df["ano_alvo"]).le(2022)
                & df["horizonte"].eq(candidate.horizonte)
            ].copy()
            features = selected_features(frame, candidate.conjunto, memory)
            rows: list[dict] = []
            for year, train, validation in expanding_folds(frame, CV_YEARS, start_year):
                threshold = float(train["target_casos"].quantile(0.75))
                model = build_estimator(spec)
                model.fit(train[features], train["target_casos"])
                metrics = score_predictions(
                    validation["target_casos"],
                    model.predict(validation[features]),
                    threshold,
                )
                rows.append({"ano_validacao": year, **metrics})
            fold_df = pd.DataFrame(rows)
            outputs.append(
                pd.DataFrame(
                    [
                        {
                            "cenario_sensibilidade": scenario,
                            "horizonte": candidate.horizonte,
                            "conjunto": candidate.conjunto,
                            "modelo": candidate.modelo,
                            "config_id": candidate.config_id,
                            "mae_media": fold_df["mae"].mean(),
                            "mae_desvio": fold_df["mae"].std(),
                            "mae_pior_fold": fold_df["mae"].max(),
                            "rmse_medio": fold_df["rmse"].mean(),
                            "mae_picos_media": fold_df["mae_picos"].mean(),
                        }
                    ]
                )
            )
    return pd.concat(outputs, ignore_index=True).sort_values(
        ["horizonte", "modelo", "conjunto", "cenario_sensibilidade"]
    )


def assert_test_locked(df: pd.DataFrame) -> None:
    """Defesa adicional para rotinas de seleção."""

    if "teste" not in set(df["split"].astype(str)):
        raise ValueError("Snapshot não contém o holdout esperado de 2024")
    if pd.to_numeric(df.loc[df["split"].eq("teste"), "ano_alvo"]).nunique() != 1:
        raise ValueError("Holdout temporal inesperado")
    if int(pd.to_numeric(df.loc[df["split"].eq("teste"), "ano_alvo"]).iloc[0]) != 2024:
        raise ValueError("O teste bloqueado deve ser 2024")


def candidate_feature_names(df: pd.DataFrame) -> set[str]:
    """Ajuda testes e auditorias a confirmar que metadados não viram features."""

    return set(df.columns) - NON_FEATURE_COLUMNS
