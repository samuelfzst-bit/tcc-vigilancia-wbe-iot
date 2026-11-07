"""Verifica a classificação exibida e a renderização sem acesso ao banco."""
from pathlib import Path
import json

import pandas as pd
import pytest

from frontend.analytics import forecast_state, prepare_forecasts, telemetry_summary, latest_forecast_series


@pytest.mark.parametrize("predicted,level,expected", [
    (1.5, "normal", "normal"), (2, "atencao", "attention"),
    (4, "alerta", "alert"), (float("nan"), "normal", "unavailable"),
    (3, "normal", "unavailable"), (3, "desconhecido", "unavailable"),
])
def test_decision_does_not_hide_invalid_predictions(predicted, level, expected):
    row = dict(previsto=predicted, nivel_previsto=level, limiar_atencao=2, limiar_alerta=4)
    assert forecast_state(row)[2] == expected


def test_telemetry_freshness_uses_latest_reading_and_counts_only_internal_gaps():
    frame = pd.DataFrame({"data_hora": pd.to_datetime([
        "2026-10-29 10:00Z", "2026-10-29 10:05Z", "2026-10-29 11:00Z"
    ])})
    assert telemetry_summary(frame, "2026-10-29 11:05Z")["status"] == "Leitura recente"
    stale = telemetry_summary(frame, "2026-10-30 11:05Z")
    assert stale["status"] == "Leitura desatualizada"
    assert stale["gaps"] == 1
    assert telemetry_summary(frame, "2026-10-29 10:30Z")["tone"] == "unavailable"


def test_normalization_does_not_change_source_and_keeps_missing_prediction():
    raw = pd.DataFrame([dict(horizonte=1, inicio_semana_alvo="2024-12-23",
                            previsto=None, observado=2, nivel_previsto="normal",
                            limiar_atencao=2, limiar_alerta=4)])
    before = raw.copy(deep=True)
    prepared, missing = prepare_forecasts(raw)
    assert not missing
    assert forecast_state(prepared.iloc[0])[2] == "unavailable"
    pd.testing.assert_frame_equal(raw, before)


@pytest.mark.parametrize("empty", [False, True])
def test_dashboard_renders_without_database(monkeypatch, empty):
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    st.cache_data.clear()
    st.cache_resource.clear()
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "frontend"))
    from frontend import data_access, query_service
    monkeypatch.setattr(query_service, "load_local_secrets", lambda root: {})

    dates = pd.date_range("2026-10-28", periods=30, freq="5min", tz="UTC")
    sensors = pd.DataFrame(dict(device_id="ESP32-TEST", data_hora=dates,
                                ph_value=7., turbidity_value=10., tds_value=300., temperature_value=24.))
    predictions = pd.DataFrame([
        dict(horizonte=h, inicio_semana_alvo=f"2024-12-{day}", observado=2,
             previsto=3., nivel_previsto="atencao", limiar_atencao=2., limiar_alerta=4.)
        for h in (1, 2) for day in (16, 23)
    ])
    monkeypatch.setattr(data_access, "build_engine", lambda url: object())
    monkeypatch.setattr(data_access, "database_url", lambda secrets: "unused")
    monkeypatch.setattr(data_access, "load_sensor_readings", lambda engine: sensors.iloc[:0] if empty else sensors.copy())
    monkeypatch.setattr(data_access, "load_predictions", lambda engine: predictions.iloc[:0] if empty else predictions.copy())
    monkeypatch.setattr(data_access, "load_historical_predictions", lambda engine: pd.DataFrame(columns=["horizonte", "inicio_semana_alvo", "observado", "previsto", "nivel_previsto", "limiar_atencao", "limiar_alerta"]))
    app = AppTest.from_file(str(root / "frontend/app.py")).run(timeout=45)
    assert not app.exception
    assert len(app.tabs) == 5
    markup = " ".join(m.value for m in app.markdown)
    assert "Sem resultado disponível" in markup if empty else "Atenção" in markup
    assert not any(r.label == "Horizonte da resposta da IA" for r in app.radio)
    assert app.toggle(key="auto_refresh").value is True
    assert not any(e.label == "Situação dos carregamentos" for e in app.expander)
    assert not any("Consulta da tela:" in c.value for c in app.caption)
    assert any("Atualizado às" in m.value for m in app.markdown)
    if not empty:
        period = app.selectbox(key="recent_period")
        assert period.value == "Últimas 24h disponíveis"
        app.selectbox(key="forecast_weeks").set_value(26).run(timeout=45)
        assert not app.exception
        # Novas leituras entram sem deixar o filtro preso a uma data antiga.
        sensors.loc[len(sensors)] = ["ESP32-TEST", pd.Timestamp("2026-10-30 00:35:08Z"), 8.25, 11., 310., 25.]
        app.button[0].click().run(timeout=45)
        assert not app.exception
        assert "29/10/2026 21:35:08" in " ".join(m.value for m in app.markdown)
        assert ">8,25<" in " ".join(m.value for m in app.markdown)
        freshness = next(m.value for m in app.markdown if "Atualizado às" in m.value)
        completed = next(m.value for m in app.metric if m.label == "Última atualização dos dados (Brasília)")
        assert completed in freshness
        comparison = app.tabs[2].dataframe[0].value
        assert comparison["data_hora"].iloc[0] == pd.Timestamp("2026-10-29 21:35:08")
        chart_specs = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
        daily = next(spec for spec in chart_specs if spec["layout"].get("xaxis", {}).get("title", {}).get("text") == "Dia (Brasília)")
        assert daily["data"][0]["x"][-1].startswith("2026-10-29T00:00:00")

        assert not any(control.key == "quality_daily_indicator" for control in app.selectbox)
        assert any(heading.value == "Análises e Comparação com a Média" for heading in app.tabs[2].subheader)
        assert not any(tab.label == "Evolução e alterações" for tab in app.tabs)
        window = next(control for control in app.slider if control.label == "Registros anteriores")
        window.set_value(12).run(timeout=45)
        assert not app.exception
        for grouping in ("5 minutos", "15 minutos", "30 minutos", "60 minutos", "Original"):
            control = next(c for c in app.selectbox if c.label == "Agrupamento do gráfico geral")
            control.set_value(grouping).run(timeout=45)
            assert not app.exception


def test_latest_execution_is_selected_by_publication_not_target_date():
    raw = pd.DataFrame([
        dict(horizonte=1, inicio_semana_alvo="2026-10-26", previsto=3, observado=2,
             nivel_previsto="atencao", limiar_atencao=2, limiar_alerta=4,
             execucao_id="old", criado_em="2026-10-27T10:00Z"),
        dict(horizonte=1, inicio_semana_alvo="2026-10-19", previsto=1, observado=1,
             nivel_previsto="normal", limiar_atencao=2, limiar_alerta=4,
             execucao_id="new", criado_em="2026-10-29T10:00Z"),
        dict(horizonte=2, inicio_semana_alvo="2026-10-26", previsto=4, observado=3,
             nivel_previsto="alerta", limiar_atencao=2, limiar_alerta=4,
             execucao_id="new", criado_em="2026-10-29T10:00Z"),
    ])
    prepared, _ = prepare_forecasts(raw)
    result = latest_forecast_series(prepared)
    assert result["execucao_id"].tolist() == ["new"]
    assert result["horizonte"].tolist() == [1]
    assert result.iloc[-1]["inicio_semana_alvo"] == pd.Timestamp("2026-10-19T00:00Z")


@pytest.mark.parametrize("observed", [None, 2.])
def test_operational_forecast_chart_respects_observation_availability(monkeypatch, observed):
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    from frontend import data_access, query_service
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr(query_service, "load_local_secrets", lambda root: {})
    monkeypatch.setattr(data_access, "build_engine", lambda url: object())
    monkeypatch.setattr(data_access, "database_url", lambda secrets: "unused")
    sensors = pd.DataFrame(columns=["device_id", "data_hora", "ph_value", "turbidity_value", "tds_value", "temperature_value"])
    forecasts = pd.DataFrame([
        dict(horizonte=1, inicio_semana_alvo=day, observado=observed,
             previsto=3.28, nivel_previsto="atencao", limiar_atencao=2., limiar_alerta=4.,
             execucao_id="operational-fixture", criado_em="2026-10-30T02:03:50Z",
             gerado_em="2026-10-30T02:03:50Z", tipo_previsao="reconstruida",
             status_observado="indisponivel" if observed is None else "provisorio",
             data_limite_clima="2026-09-30")
        for day in ("2026-09-27", "2026-10-04")
    ])
    monkeypatch.setattr(data_access, "load_sensor_readings", lambda engine: sensors.copy())
    monkeypatch.setattr(data_access, "load_predictions", lambda engine: forecasts.copy())
    monkeypatch.setattr(data_access, "load_historical_predictions", lambda engine: pd.DataFrame(columns=["horizonte", "inicio_semana_alvo", "observado", "previsto", "nivel_previsto", "limiar_atencao", "limiar_alerta"]))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/app.py")).run(timeout=45)
    assert not app.exception
    markup = " ".join(m.value for m in app.markdown)
    assert "Semana prevista: 04/10/2026" in markup
    assert "Reconstruída" in markup
    assert "29/10/2026 23:03:50" in markup
    figure = json.loads(app.get("plotly_chart")[0].proto.spec)
    names = [trace["name"] for trace in figure["data"]]
    metrics = [metric.label for metric in app.metric]
    if observed is None:
        assert "Observado provisório" not in names
        assert not any("Erro absoluto" in label or "Viés" in label for label in metrics)
        assert "Evolução das estimativas operacionais" in figure["layout"]["title"]["text"]
        assert any("Casos observados indisponíveis" in caption.value for caption in app.caption)
    else:
        assert "Observado provisório" in names
        assert "Erro absoluto médio provisório" in metrics


@pytest.mark.parametrize("unavailable", [False, True])
def test_historical_validation_keeps_full_timeline_separate_from_operational(monkeypatch, unavailable):
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    from frontend import data_access, query_service
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr(query_service, "load_local_secrets", lambda root: {})
    monkeypatch.setattr(data_access, "build_engine", lambda url: object())
    monkeypatch.setattr(data_access, "database_url", lambda secrets: "unused")
    sensors = pd.DataFrame(columns=["device_id", "data_hora", "ph_value", "turbidity_value", "tds_value", "temperature_value"])
    operational = pd.DataFrame([dict(horizonte=1, inicio_semana_alvo="2026-10-04", observado=None,
        previsto=3.28, nivel_previsto="atencao", limiar_atencao=2., limiar_alerta=4.)])
    history = pd.DataFrame([dict(horizonte=h, inicio_semana_alvo=day, observado=2.,
        previsto=3. if h == 1 else 5., nivel_previsto="atencao" if h == 1 else "alerta",
        limiar_atencao=2., limiar_alerta=4.)
        for h in (1, 2) for day in pd.date_range("2023-11-05", periods=60, freq="7D", tz="UTC")])
    def historical_loader(engine):
        if unavailable:
            raise RuntimeError("fixture unavailable")
        return history.copy()
    monkeypatch.setattr(data_access, "load_sensor_readings", lambda engine: sensors.copy())
    monkeypatch.setattr(data_access, "load_predictions", lambda engine: operational.copy())
    monkeypatch.setattr(data_access, "load_historical_predictions", historical_loader)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/app.py")).run(timeout=45)
    assert not app.exception
    assert [tab.label for tab in app.tabs][:2] == ["Visão geral", "Validação Histórica"]
    assert "Semana prevista: 04/10/2026" in " ".join(m.value for m in app.markdown)
    if unavailable:
        assert any("Avaliação histórica indisponível" in warning.value for warning in app.warning)
        assert len(app.get("plotly_chart")) == 1
        return
    def historical_figure():
        return json.loads(app.get("plotly_chart")[1].proto.spec)
    figure = historical_figure()
    assert len(figure["data"][0]["x"]) == 60
    assert figure["data"][0]["x"][0].startswith("2023-11-05")
    assert figure["data"][0]["name"] == "Casos observados"
    historical_markup = " ".join(m.value for m in app.tabs[1].markdown)
    assert "historical-cards" in historical_markup
    assert "Erro absoluto médio (MAE)" in historical_markup and "1,00 casos" in historical_markup
    assert "Semanas comparadas" in historical_markup and ">60<" in historical_markup
    assert not any(control.key == "historical_horizon" for control in app.selectbox)
    assert not any(metric.value == "3,00 casos" for metric in app.metric if metric.label == "Erro absoluto médio (MAE)")


def test_one_week_policy_never_falls_back_to_two_weeks_or_old_execution():
    raw = pd.DataFrame([
        dict(horizonte=1, inicio_semana_alvo="2026-09-27", execucao_id="old", criado_em="2026-10-28T00:00Z"),
        dict(horizonte=2, inicio_semana_alvo="2026-10-04", execucao_id="new", criado_em="2026-10-30T00:00Z"),
    ])
    raw["inicio_semana_alvo"] = pd.to_datetime(raw["inicio_semana_alvo"], utc=True)
    assert latest_forecast_series(raw).empty
    assert latest_forecast_series(raw.iloc[1:].drop(columns=["criado_em", "execucao_id"])).empty
