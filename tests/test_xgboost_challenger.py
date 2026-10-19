import pandas as pd
from sklearn.dummy import DummyRegressor

import src.xgboost_challenger as challenger
from src.xgboost_challenger import (
    XGBoostSpec,
    decide_challenger,
    run_challenger_cv,
    select_xgboost_configs,
    xgboost_specs,
)


def small_frame() -> pd.DataFrame:
    rows = []
    for horizon in (1, 2):
        for year in range(2016, 2025):
            for week in (1, 2, 3, 4):
                start = pd.Timestamp.fromisocalendar(year, week, 1)
                rows.append(
                    {
                        "horizonte": horizon,
                        "inicio_semana_t": start,
                        "inicio_semana_alvo": start + pd.Timedelta(days=7 * horizon),
                        "ano_alvo": year,
                        "target_casos": float((year + week + horizon) % 6),
                        "precipitacao_t": float(week),
                        "semana_alvo_sin": week / 10,
                        "semana_alvo_cos": week / 20,
                    }
                )
    return pd.DataFrame(rows)


def test_xgboost_grid_is_small_and_predefined():
    specs = xgboost_specs()
    assert len(specs) == 8
    assert len({spec.config_id for spec in specs}) == 8
    assert {spec.max_depth for spec in specs} == {2, 3}


def test_challenger_cv_never_uses_2023_or_2024(monkeypatch):
    monkeypatch.setattr(
        challenger, "build_estimator", lambda spec: DummyRegressor(strategy="mean")
    )
    monkeypatch.setattr(
        challenger, "build_xgboost", lambda spec: DummyRegressor(strategy="mean")
    )
    specs = [XGBoostSpec("teste", 10, 2, 0.05)]
    metrics = run_challenger_cv(
        small_frame(), specs=specs, validation_years=(2018, 2019, 2020)
    )
    assert set(metrics["ano_validacao"]) == {2018, 2019, 2020}
    assert 2023 not in set(metrics["ano_validacao"])
    assert 2024 not in set(metrics["ano_validacao"])


def test_selection_uses_lowest_cv_mae():
    summary = pd.DataFrame(
        [
            {"horizonte": 1, "modelo": "xgboost_poisson", "config_id": "a", "mae_media": 1.7, "rmse_medio": 2.0, "mae_desvio": 0.2},
            {"horizonte": 1, "modelo": "xgboost_poisson", "config_id": "b", "mae_media": 1.5, "rmse_medio": 2.1, "mae_desvio": 0.3},
            {"horizonte": 2, "modelo": "xgboost_poisson", "config_id": "c", "mae_media": 1.8, "rmse_medio": 2.2, "mae_desvio": 0.2},
        ]
    )
    selected = select_xgboost_configs(summary)
    assert selected.set_index("horizonte").loc[1, "config_id"] == "b"
    assert selected.set_index("horizonte").loc[2, "config_id"] == "c"


def test_xgboost_only_replaces_poisson_if_every_rule_passes():
    validation = pd.DataFrame(
        [
            {"horizonte": 1, "modelo": "poisson", "config_id": "alpha=1", "mae": 1.5, "mae_picos": 2.0},
            {"horizonte": 1, "modelo": "xgboost_poisson", "config_id": "x1", "mae": 1.4, "mae_picos": 2.1},
            {"horizonte": 2, "modelo": "poisson", "config_id": "alpha=1", "mae": 1.7, "mae_picos": 2.5},
            {"horizonte": 2, "modelo": "xgboost_poisson", "config_id": "x2", "mae": 1.65, "mae_picos": 2.4},
        ]
    )
    cv = pd.DataFrame(
        [
            {"horizonte": 1, "modelo": "poisson", "config_id": "alpha=1", "mae_media": 1.6, "mae_desvio": 0.20},
            {"horizonte": 1, "modelo": "xgboost_poisson", "config_id": "x1", "mae_media": 1.5, "mae_desvio": 0.22},
            {"horizonte": 2, "modelo": "poisson", "config_id": "alpha=1", "mae_media": 1.7, "mae_desvio": 0.20},
            {"horizonte": 2, "modelo": "xgboost_poisson", "config_id": "x2", "mae_media": 1.6, "mae_desvio": 0.21},
        ]
    )
    decision = decide_challenger(validation, cv).set_index("horizonte")
    assert bool(decision.loc[1, "xgboost_substitui_poisson"])
    assert not bool(decision.loc[2, "xgboost_substitui_poisson"])
    assert decision.loc[2, "modelo_recomendado"] == "poisson"
