import copy

import pandas as pd
import pytest

from src.final_evaluation import (
    EXPECTED_DATASET_SHA256,
    block_bootstrap_mae_interval,
    build_frozen_protocol,
    classification_metrics,
    evaluate_locked_2024,
    validate_frozen_protocol,
)


def final_frame() -> pd.DataFrame:
    rows = []
    for horizon in (1, 2):
        for year in range(2015, 2025):
            for week in range(1, 9):
                start = pd.Timestamp.fromisocalendar(year, week, 1)
                target = float((year + week + horizon) % 7)
                rows.append(
                    {
                        "horizonte": horizon,
                        "inicio_semana_t": start,
                        "inicio_semana_alvo": start
                        + pd.Timedelta(days=7 * horizon),
                        "ano_alvo": year,
                        "semana_alvo": week,
                        "target_casos": target,
                        "versao_dataset": "dataset_modelagem_v1_20260927",
                        "temperatura_media_t": 18.0 + week,
                        "precipitacao_t": float(week * 3),
                        "umidade_media_t": 60.0 + week,
                        "semana_alvo_sin": week / 10,
                        "semana_alvo_cos": week / 20,
                        "casos_conhecidos_lag_2": float((week + 1) % 7),
                        "casos_conhecidos_lag_3": float((week + 2) % 7),
                        "casos_conhecidos_lag_4": float((week + 3) % 7),
                        "casos_conhecidos_lag_5": float((week + 4) % 7),
                        "casos_conhecidos_lag_52": float((year + week) % 7),
                        "media_conhecida_lags_2_5": 3.0,
                    }
                )
    return pd.DataFrame(rows)


def frozen_protocol(frame: pd.DataFrame) -> dict:
    return build_frozen_protocol(
        frame,
        EXPECTED_DATASET_SHA256,
        created_at_utc="20261016T000000Z",
        git_commit="teste",
    )


def test_freeze_does_not_depend_on_2024_target():
    original = final_frame()
    changed = original.copy()
    changed.loc[changed["ano_alvo"].eq(2024), "target_casos"] = 9999.0
    protocol_a = frozen_protocol(original)
    protocol_b = frozen_protocol(changed)
    assert protocol_a == protocol_b


def test_protocol_detects_any_change_after_freeze():
    protocol = frozen_protocol(final_frame())
    validate_frozen_protocol(protocol)
    tampered = copy.deepcopy(protocol)
    tampered["campeoes"][0]["limiar_alerta"] += 1
    with pytest.raises(ValueError, match="alterado"):
        validate_frozen_protocol(tampered)


def test_final_evaluation_uses_only_frozen_poisson():
    frame = final_frame()
    protocol = frozen_protocol(frame)
    metrics, alerts, predictions, models = evaluate_locked_2024(frame, protocol)
    champion = metrics.loc[metrics["modelo_congelado"]]
    assert set(champion["modelo"]) == {"poisson_final"}
    assert set(champion["horizonte"]) == {1, 2}
    assert champion["n"].eq(8).all()
    assert len(predictions) == 16
    assert set(alerts["horizonte"]) == {1, 2}
    assert set(models) == {1, 2}


def test_alert_metrics_are_consistent():
    metrics = classification_metrics([0, 5, 6, 1], [1, 4, 7, 5], threshold=5)
    assert metrics["verdadeiros_positivos"] == 1
    assert metrics["falsos_positivos"] == 1
    assert metrics["falsos_negativos"] == 1
    assert metrics["verdadeiros_negativos"] == 1
    assert metrics["f1_alerta"] == pytest.approx(0.5)


def test_block_bootstrap_interval_is_deterministic():
    first = block_bootstrap_mae_interval(
        [1, 2, 3, 4], [1, 1, 4, 6], n_bootstrap=100, random_state=7
    )
    second = block_bootstrap_mae_interval(
        [1, 2, 3, 4], [1, 1, 4, 6], n_bootstrap=100, random_state=7
    )
    assert first == second
    assert first[0] <= first[1]
