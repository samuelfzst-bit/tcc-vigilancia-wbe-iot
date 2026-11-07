"""Fixtures determinísticas; não leem configuração nem usam o banco real."""
import math

import numpy as np
import pandas as pd
import pytest

from frontend.analytics import (
    LABELS, DisplayRangeError, analyze, break_line_at_gaps,
    daily_summary, grouped_series, hide_edge_zeros, prepare, prepare_forecasts,
    individual_statistics, advance_analysis, reading_quality,
)


def readings(values):
    frame = pd.DataFrame({"data_hora": pd.date_range("2026-11-01", periods=len(values), freq="5min", tz="UTC"), "device_id": "fixture"})
    for col in LABELS:
        frame[col] = values
    return frame


@pytest.mark.parametrize("col", list(LABELS))
def test_reading_farol_distinguishes_zero_missing_and_valid_for_each_sensor(col):
    source = readings([7.] * 5)
    source[col] = [7., 0., np.nan, np.inf, ""]
    source.loc[2, next(c for c in LABELS if c != col)] = 0.
    before = source.copy(deep=True)
    result = reading_quality(source)
    assert result["Farol"].str[0].tolist() == ["🟢", "🟡", "🔴", "🔴", "🔴"]
    assert LABELS[col] in result.iloc[1]["Motivo"]
    assert "Ausente/inválido" in result.iloc[2]["Motivo"] and "Zero:" in result.iloc[2]["Motivo"]
    pd.testing.assert_frame_equal(source, before)


def test_individual_statistics_preserve_constant_values_zero_and_missing():
    stats = individual_statistics(readings([7., 7., np.nan, 7.]), "ph_value")
    assert stats == {"minimum": 7., "mean": 7., "maximum": 7., "std": 0.}
    assert individual_statistics(readings([0., 2.]), "ph_value")["mean"] == 1.
    assert pd.isna(individual_statistics(readings([7.]), "ph_value")["std"])


def test_analysis_compares_updates_and_preserves_delta_on_widget_reruns():
    first = advance_analysis(None, {"mean": 7., "std": np.nan}, "first")
    assert first["changes"] == {"mean": 0., "std": 0.}
    assert first["compared_at"] == "first"
    changed = advance_analysis(first, {"mean": 8., "std": 1.}, "second")
    assert changed["changes"] == {"mean": 1., "std": 0.}
    assert changed["compared_at"] == "first"
    assert advance_analysis(changed, {"mean": 8., "std": 1.}, "second") is changed
    unchanged = advance_analysis(changed, {"mean": 8., "std": 1.}, "third")
    assert unchanged["changes"] == {"mean": 0., "std": 0.}
    assert unchanged["compared_at"] == "second"
    falling = advance_analysis(unchanged, {"mean": 7.5, "std": 0.}, "fourth")
    assert falling["changes"] == {"mean": -.5, "std": -1.}


def test_current_value_never_enters_its_own_reference_and_requires_twelve_previous():
    source = readings([*range(12), 100.])
    before = source.copy(deep=True)
    result = analyze(source, 48, 3.)
    assert pd.isna(result.iloc[11]["ph_value_media"])
    assert result.iloc[12]["ph_value_media"] == pytest.approx(5.5)
    assert result.iloc[12]["ph_value_std"] == pytest.approx(math.sqrt(13))
    assert pd.isna(result.iloc[12]["ph_value_change_z"])  # Só 11 diferenças anteriores.
    pd.testing.assert_frame_equal(source, before)


@pytest.mark.parametrize("window,mean", [(12, 41.5), (48, 23.5), (96, 23.5)])
def test_window_counts_previous_records(window, mean):
    result = analyze(readings([*range(48), 100]), window, 3.)
    assert result.iloc[-1]["ph_value_media"] == pytest.approx(mean)


@pytest.mark.parametrize("threshold,flag", [(2., True), (3., True), (4., False)])
def test_threshold_is_used_dynamically(threshold, flag):
    changes = [-1., 0., 1.] * 8
    source = readings([100., *(100. + np.cumsum(changes)), 100. + 3.1 / 0.6745])
    result = analyze(source, 48, threshold)
    for col in LABELS:
        assert result.iloc[-1][col + "_change_z"] == pytest.approx(3.1)
        assert bool(result.iloc[-1][col + "_desvio"]) is flag

def test_zero_variance_and_insufficient_valid_history_are_not_false_diagnoses():
    constant = analyze(readings([7.] * 14), 48, 3.)
    assert constant["ph_value_z"].isna().all()
    assert not constant["ph_value_desvio"].any()
    missing = analyze(readings([np.nan, *range(11), 100.]), 48, 3.)
    assert pd.isna(missing.iloc[-1]["ph_value_z"])


@pytest.mark.parametrize("jump,flag", [(1., False), (-1., False), (20., True), (-20., True)])
def test_robust_change_rule_is_symmetric_for_all_sensors(jump, flag):
    history = [100., *(100. + np.cumsum([-1., 0., 1.] * 16))]
    source = readings([*history, history[-1] + jump, history[-1] + jump])
    result = analyze(source, 48)
    for col in LABELS:
        assert bool(result.iloc[-2][col + "_desvio"]) is flag
        assert not bool(result.iloc[-1][col + "_desvio"])
    source.loc[source.index[-2:], "data_hora"] += pd.Timedelta(hours=1)
    assert not analyze(source, 48)["ph_value_desvio"].tail(2).any()


def test_robust_rule_is_invariant_to_units_and_offset():
    values = [100., *(100. + np.cumsum([-1., 0., 1.] * 16)), 120.]
    base = analyze(readings(values), 48)
    converted = analyze(readings(np.asarray(values) * 1.8 + 32), 48)
    np.testing.assert_allclose(base["ph_value_change_z"], converted["ph_value_change_z"], equal_nan=True)

@pytest.mark.parametrize("choice,expected", [
    ("Original", list(range(12))), ("5 minutos", list(range(12))),
    ("15 minutos", [1., 4., 7., 10.]),
    ("30 minutos", [2.5, 8.5]), ("60 minutos", [5.5]),
])
def test_each_aggregation_has_expected_means_and_leaves_source_unchanged(choice, expected):
    frame = readings(list(range(1, 13)))
    before = frame.copy(deep=True)
    series = grouped_series(frame, "ph_value", choice)
    assert series.tolist() == pytest.approx([v + 1 for v in expected])
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("col", list(LABELS))
def test_edge_zeros_are_hidden_for_every_sensor_even_when_flagged(col):
    frame = readings([0., 0., 3., 0., 4., 0., 0.])
    frame[col + "_desvio"] = False
    before = frame.copy(deep=True)
    hidden = hide_edge_zeros(frame, col)
    assert hidden[col].isna().tolist() == [True, True, False, False, False, True, True]
    assert hidden.iloc[3][col] == 0
    pd.testing.assert_frame_equal(frame, before)
    frame.loc[0, col + "_desvio"] = True
    assert pd.isna(hide_edge_zeros(frame, col).iloc[0][col])


def test_visual_gap_adds_only_empty_points_without_interpolation():
    frame = readings([4., 5., 6.])
    frame.loc[2, "data_hora"] = pd.Timestamp("2026-11-01 01:00Z")
    before = frame.copy(deep=True)
    chart = break_line_at_gaps(frame, ["ph_value"])
    assert len(chart) == 4
    assert chart["ph_value"].dropna().tolist() == [4., 5., 6.]
    assert chart.loc[chart["ph_value"].isna(), "data_hora"].iloc[0] == pd.Timestamp("2026-11-01 00:10Z")
    pd.testing.assert_frame_equal(frame, before)


def test_daily_percentage_uses_analyzable_values_only():
    analyzed = analyze(readings([100., *(100. + np.cumsum([-1., 0., 1.] * 4)), 120.]), 48)
    daily = daily_summary(analyzed, "ph_value")
    assert daily.iloc[0]["leituras_validas"] == 14
    assert daily.iloc[0]["analisaveis"] == 1
    assert daily.iloc[0]["percentual_sinalizado"] == 100
    unavailable = daily_summary(analyze(readings([1., 2.]), 48, 3.), "ph_value")
    assert pd.isna(unavailable.iloc[0]["percentual_sinalizado"])


def test_invalid_timestamps_and_numeric_values_are_reported_without_mutation():
    raw = readings([7., 8.])
    raw["data_hora"] = ["invalid", "2026-11-01T00:00:00Z"]
    raw["ph_value"] = ["bad", np.inf]
    clean, missing, invalid = prepare(raw)
    assert not missing and invalid == 1
    assert len(clean) == 1 and pd.isna(clean.iloc[0]["ph_value"])


def test_pathological_display_range_is_bounded_before_dense_resampling():
    frame = readings([1., 2.])
    frame["data_hora"] = pd.to_datetime(["1900-01-01", "2200-01-01"], utc=True)
    with pytest.raises(DisplayRangeError):
        grouped_series(frame, "ph_value", "5 minutos")
    assert len(grouped_series(frame, "ph_value", "Original")) == 2


def test_forecast_normalization_enforces_existing_one_or_two_week_contract():
    raw = pd.DataFrame([
        dict(horizonte=h, inicio_semana_alvo="2026-11-01", observado=1,
             previsto=1.5, nivel_previsto="normal", limiar_atencao=2, limiar_alerta=4)
        for h in (1, 2, 0, .5, -1, 3)
    ])
    clean, missing = prepare_forecasts(raw)
    assert not missing
    assert clean["horizonte"].tolist() == [1., 2.]


def test_unavailable_observation_is_never_coerced_to_zero_or_used_for_comparison():
    raw = pd.DataFrame([
        dict(horizonte=2, inicio_semana_alvo="2026-10-04", observado=4.,
             status_observado="indisponivel", previsto=3.28, nivel_previsto="atencao",
             limiar_atencao=2, limiar_alerta=4),
        dict(horizonte=2, inicio_semana_alvo="2026-09-27", observado=0.,
             status_observado="provisorio", previsto=2.49, nivel_previsto="atencao",
             limiar_atencao=2, limiar_alerta=4),
    ])
    clean, missing = prepare_forecasts(raw)
    assert not missing
    assert pd.isna(clean.iloc[-1]["observado"])
    assert clean.iloc[0]["observado"] == 0
    assert raw.iloc[0]["observado"] == 4


def test_historical_metrics_include_zero_observed_and_exclude_missing_pairs():
    from frontend.analytics import historical_metrics
    frame = pd.DataFrame({"observado": [0., 2., None], "previsto": [1., 4., 999.]})
    before = frame.copy(deep=True)
    scores = historical_metrics(frame)
    assert scores["weeks"] == 2
    assert scores["mae"] == 1.5
    assert scores["bias"] == 1.5
    assert abs(scores["rmse"] - 2.5 ** .5) < 1e-10
    assert historical_metrics(frame.iloc[2:]) is None
    pd.testing.assert_frame_equal(frame, before)
