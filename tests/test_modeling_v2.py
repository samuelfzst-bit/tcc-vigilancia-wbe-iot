import pandas as pd

from src.modeling_v2 import (
    ModelSpec,
    assert_test_locked,
    expanding_folds,
    run_temporal_cv,
    selected_features,
    summarize_cv,
)


def modeling_frame() -> pd.DataFrame:
    rows = []
    for horizon in (1, 2):
        for year in range(2015, 2025):
            for week in (1, 2, 3, 4):
                start = pd.Timestamp.fromisocalendar(year, week, 1)
                rows.append(
                    {
                        "horizonte": horizon,
                        "inicio_semana_t": start,
                        "inicio_semana_alvo": start + pd.Timedelta(days=7 * horizon),
                        "ano_alvo": year,
                        "semana_alvo": week,
                        "target_casos": (year + week + horizon) % 7,
                        "split": "teste"
                        if year == 2024
                        else ("validacao" if year == 2023 else "treino"),
                        "casos_conhecidos_lag_2": float((week + 1) % 5),
                        "casos_conhecidos_lag_3": float((week + 2) % 5),
                        "casos_conhecidos_lag_4": float((week + 3) % 5),
                        "casos_conhecidos_lag_5": float((week + 4) % 5),
                        "casos_conhecidos_lag_8": float(week),
                        "casos_conhecidos_lag_52": float((week + year) % 6),
                        "media_conhecida_lags_2_5": 2.0,
                        "temperatura_media_t": 20.0 + week,
                        "temperatura_media_lag_8": 19.0 + week,
                        "precipitacao_t": float(week * 2),
                        "precipitacao_acum_8s": float(week * 10),
                        "semana_alvo_sin": 0.1 * week,
                        "semana_alvo_cos": 0.2 * week,
                    }
                )
    return pd.DataFrame(rows)


def test_expanding_folds_never_include_future():
    frame = modeling_frame().loc[lambda x: x["horizonte"].eq(1)]
    for year, train, validation in expanding_folds(frame, (2018, 2019, 2020)):
        assert train["ano_alvo"].max() < year
        assert set(validation["ano_alvo"]) == {year}


def test_short_memory_removes_long_windows():
    frame = modeling_frame()
    features = selected_features(frame, "combinado", memory="short")
    assert "temperatura_media_t" in features
    assert "casos_conhecidos_lag_2" in features
    assert "temperatura_media_lag_8" not in features
    assert "precipitacao_acum_8s" not in features
    assert "casos_conhecidos_lag_52" not in features


def test_cv_uses_only_requested_past_years():
    frame = modeling_frame()
    specs = [ModelSpec("poisson", "alpha=1", {"alpha": 1.0})]
    metrics = run_temporal_cv(frame, specs=specs, validation_years=(2021, 2022))
    assert set(metrics["ano_validacao"]) == {2021, 2022}
    assert 2023 not in set(metrics["ano_validacao"])
    assert 2024 not in set(metrics["ano_validacao"])
    summary = summarize_cv(metrics)
    assert summary["folds"].eq(2).all()


def test_locked_test_is_2024():
    assert_test_locked(modeling_frame())
