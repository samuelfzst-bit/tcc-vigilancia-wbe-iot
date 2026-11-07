"""Dashboard WBE-IoT. Usa o data_access.py original; não gera dados fictícios."""
from __future__ import annotations

from datetime import datetime
from html import escape
import importlib
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Vigilância WBE-IoT",page_icon="🌊",layout="wide",initial_sidebar_state="collapsed")
COLORS={"ph_value":"#38bdf8","turbidity_value":"#fbbf24","tds_value":"#a78bfa","temperature_value":"#fb7185"}
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from frontend.presentation import (
    apply_style, render_prediction, render_telemetry_summary, render_update_status,
)
from frontend.analytics import (
    LABELS, AGGREGATIONS, MIN_HISTORY, prepare, analyze, grouped_series, individual_statistics, advance_analysis, hide_edge_zeros, reading_quality,
    break_line_at_gaps, daily_summary, DisplayRangeError,
    prepare_forecasts, latest_forecast_series, historical_metrics,
)
from frontend.query_service import (
    BRASILIA, REFRESH_SECONDS, ConfigurationError, execute_read, latest_success_at, load_local_secrets,
    refresh_due, update_status,
)
apply_style()

@st.cache_resource(show_spinner=False)
def get_engine():
    access=importlib.import_module("frontend.data_access")
    secrets = load_local_secrets(ROOT)
    try:
        url = access.database_url(secrets)
    except RuntimeError:
        raise ConfigurationError("Configuração de acesso ausente ou inválida.") from None
    return access.build_engine(url)


@st.cache_data(ttl=REFRESH_SECONDS, max_entries=1, show_spinner=False)
def load_dashboard_sources():
    access = importlib.import_module("frontend.data_access")
    return (
        execute_read(lambda: access.load_sensor_readings(get_engine()), "sensors"),
        execute_read(lambda: access.load_predictions(get_engine()), "forecasts"),
        execute_read(lambda: access.load_historical_predictions(get_engine()), "historical_forecasts"),
    )


CALENDAR_COLUMNS = {"inicio_semana_alvo", "inicio_semana_t", "data_corte", "data_limite_clima"}
TIMESTAMP_COLUMNS = {"data_hora", "criado_em", "gerado_em"}


def display_dates(frame, *, for_table=False):
    display = frame.copy()
    for col in display:
        if col in CALENDAR_COLUMNS:
            display[col] = pd.to_datetime(display[col], errors="coerce").dt.date
        elif col in TIMESTAMP_COLUMNS or pd.api.types.is_datetime64_any_dtype(display[col]):
            local = pd.to_datetime(display[col], errors="coerce", utc=True).dt.tz_convert(BRASILIA)
            display[col] = local.dt.tz_localize(None) if for_table else local
    return display


def value(x,suffix=""):
    return "—" if pd.isna(x) else f"{x:.2f}{suffix}".replace(".", ",")

def table(frame, **kwargs):
    """Formata somente a visualização, preservando os valores para análise."""
    display = display_dates(frame, for_table=True)
    date_col = next((c for c in ("data_hora", "inicio_semana_alvo") if c in display), None)
    if date_col:
        display = display.sort_values(date_col, ascending=False, na_position="last").reset_index(drop=True)
    names = {**LABELS, "data_hora":"Data e hora (Brasília)", "inicio_semana_alvo":"Semana de referência",
             "previsto":"Casos estimados", "observado":"Casos observados provisórios", "nivel_previsto":"Classificação",
             "limiar_atencao":"Limiar de atenção", "limiar_alerta":"Limiar de alerta",
             "device_id":"Dispositivo", "indicadores_com_desvio":"Indicadores com alteração relevante",
             "erro_previsto_menos_observado":"Diferença (estimado − observado provisório)", "criado_em":"Publicação (Brasília)",
             "observado_provisorio":"Observado provisório", "status_observado":"Disponibilidade do observado",
             "gerado_em":"Geração (Brasília)", "tipo_previsao":"Tipo de previsão", "data_corte":"Corte dos dados",
             "data_limite_clima":"Dados climáticos até"}
    config = {c: st.column_config.NumberColumn(names.get(c, str(c)), format="%.2f")
              for c in display if pd.api.types.is_float_dtype(display[c])}
    for c in display:
        if c not in config and c in names:
            config[c] = st.column_config.Column(names[c])
    for col in display.columns:
        if col in CALENDAR_COLUMNS:
            config[col] = st.column_config.DateColumn(names.get(col, col), format="DD/MM/YYYY")
        elif pd.api.types.is_datetime64_any_dtype(display[col]):
            config[col] = st.column_config.DatetimeColumn(
                names.get(col, col), format="DD/MM/YYYY HH:mm:ss"
            )
    st.dataframe(display, column_config=config, **kwargs)


def show(fig, navigable=False, *, date_only=False, sensor_overview=False):
    # HTML se ajusta à largura no celular; o título SVG permanece no desktop.
    if fig.layout.title.text and not sensor_overview:
        st.markdown(f'<p class="mobile-chart-title">{escape(str(fig.layout.title.text))}</p>', unsafe_allow_html=True)
    date_format = "%d/%m/%Y" if date_only else "%d/%m/%Y %H:%M:%S"
    tick_format = "%d/%m/%Y" if date_only else "%d/%m/%Y<br>%H:%M:%S"
    date_suffix = "" if date_only else " (Brasília)"
    # Somente eixos temporais: histogramas e boxplots mantêm suas escalas.
    for trace in fig.data:
        values = getattr(trace, "x", None)
        if values is not None and len(values) and isinstance(values[0], (pd.Timestamp, datetime, np.datetime64)):
            if not date_only:
                trace.x = pd.to_datetime(values, utc=True).tz_convert(BRASILIA).tz_localize(None)
            if trace.type in ("scatter", "scattergl") and trace.hoverinfo != "skip":
                trace.hovertemplate = "%{x|" + date_format + "}" + date_suffix + "<br>Valor: %{y:.2f}<extra>%{fullData.name}</extra>"
            axis = "xaxis" + ((getattr(trace, "xaxis", None) or "x")[1:])
            fig.update_layout({axis: dict(nticks=4, tickformat=tick_format, hoverformat=date_format)})
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#081923", plot_bgcolor="#0c202b",
        font=dict(family="Segoe UI, sans-serif", color="#e7f1f5", size=12),
        colorway=list(COLORS.values()),
        margin=dict(l=15,r=15,t=85,b=25),
        hoverlabel=dict(bgcolor="#173746",font_color="#e7f1f5"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
    )
    if sensor_overview:
        fig.update_layout(title=dict(text=""), margin=dict(t=120,b=65), legend=dict(y=1.10,yanchor="bottom",x=0,xanchor="left",traceorder="normal"))
    fig.update_xaxes(gridcolor="#203b49", zerolinecolor="#365360", automargin=True,
                     rangeselector=dict(bgcolor="#173746", activecolor="#326176", font_color="#e7f1f5"))
    fig.update_yaxes(gridcolor="#203b49", zerolinecolor="#365360", automargin=True)
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="#67c5da", spikethickness=1)
    fig.update_layout(autosize=True, uirevision=str(fig.layout.title.text), hoverdistance=40)
    st.plotly_chart(fig, width="stretch", config={
        "responsive": True, "scrollZoom": False, "displaylogo": False,
        "displayModeBar": True, "toImageButtonOptions": {"format": "png", "scale": 2},
        "doubleClick": "autosize", "modeBarButtonsToRemove": ["lasso2d", "select2d", "zoomIn2d", "zoomOut2d"],
    })

def export(frame,key):
    st.download_button("Exportar CSV",display_dates(frame).to_csv(index=False).encode("utf-8-sig"),file_name=key+".csv",mime="text/csv",key=key)

def empty():
    st.info("Sem leituras disponíveis neste recorte. Confira o carregamento e o período selecionado.")

def latest_cards(frame):
    cards = []
    last = frame.iloc[-1] if not frame.empty else None
    prev = frame.iloc[-2] if len(frame) > 1 else None
    for col, label in LABELS.items():
        displayed = value(last[col], " °C" if col == "temperature_value" else "") if last is not None else "—"
        capsule = '<span class="sensor-change neutral">Sem comparação</span>'
        if prev is not None and pd.notna(prev[col]) and pd.notna(last[col]):
            difference = round(float(last[col] - prev[col]), 2)
            tone = "up" if difference > 0 else "down" if difference < 0 else "neutral"
            arrow = "↑" if difference > 0 else "↓" if difference < 0 else "="
            amount = value(abs(difference))
            capsule = f'<span class="sensor-change {tone}" title="Variação absoluta em relação ao registro anterior">{arrow} {amount}</span>'
        cards.append(f'<section class="sensor-card"><div class="sensor-name">{escape(label)}</div><div class="sensor-value-row"><strong>{escape(displayed)}</strong>{capsule}</div><div class="sensor-comparison">vs. registro anterior</div></section>')
    st.markdown('<div class="sensor-cards">' + ''.join(cards) + '</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Filtros")
    with st.expander("Atualização"):
        auto_refresh = st.toggle("Atualização automática", value=True, key="auto_refresh")
        st.caption("A cada 30 segundos enquanto esta sessão estiver aberta.")
        if st.button("Atualizar agora", width="stretch", key="manual_refresh"):
            load_dashboard_sources.clear()
            st.rerun()

poll_now = time.monotonic()
if refresh_due(poll_now, st.session_state.get("last_poll_started")):
    st.session_state["last_poll_started"] = poll_now
source_results = load_dashboard_sources()
sensor_result, forecast_result, historical_result = source_results
historical, historical_missing = prepare_forecasts(historical_result.frame)
raw, forecasts = sensor_result.frame, forecast_result.frame
sensor_error = sensor_result.issue.message if sensor_result.issue else None
forecast_error = forecast_result.issue.message if forecast_result.issue else None
sensors,missing,invalid=prepare(raw)
sensors["data_hora"] = pd.to_datetime(sensors["data_hora"], utc=True).dt.tz_convert(BRASILIA)
p, forecast_missing = prepare_forecasts(forecasts)
forecast_invalid = max(0, len(forecasts) - len(p)) if not forecast_missing else 0

@st.fragment(run_every=REFRESH_SECONDS if auto_refresh else None)
def refresh_indicator():
    now = time.monotonic()
    if refresh_due(now, st.session_state.get("last_poll_started"), auto_refresh):
        st.session_state["last_poll_started"] = now
        # TTL coordena leituras entre sessões. O timer não limpa o cache global.
        st.rerun(scope="app")
    label, tone, detail = update_status(
        source_results, invalid_contract=bool((missing and not sensor_error) or (forecast_missing and not forecast_error) or (historical_missing and not historical_result.issue) or invalid or forecast_invalid)
    )
    render_update_status(label, tone, detail, paused=not auto_refresh)

heading, freshness = st.columns([3, 2], vertical_alignment="center")
with heading:
    st.title("Vigilância WBE-IoT")
with freshness:
    refresh_indicator()

with st.sidebar:
    ids=sorted(sensors["device_id"].dropna().astype(str).unique())
    chosen=None
    if len(ids)==1:
        chosen=ids[0]
        st.info("ESP32: "+chosen)
    elif len(ids)>1:
        st.warning("Há mais de um ID no retorno. Escolha a placa correta; séries não serão misturadas.")
        chosen=st.selectbox("Dispositivo",ids)
    else:
        st.caption("Dispositivo indisponível.")
    with st.expander("Análise estatística"):
        window=st.slider("Registros anteriores",MIN_HISTORY,96,48,12,
                         help="A leitura atual não participa da própria referência. A janela é por registros, não por horas.")
        threshold=3.5
        st.caption("Pontos vermelhos: escore robusto das mudanças entre leituras, |M| > 3,5. Sem percentual fixo.")
        aggregation=st.selectbox("Agrupamento do gráfico geral",list(AGGREGATIONS),
                                help="Original mantém cada leitura. Os demais agrupamentos exibem a média do intervalo, sem alterar a análise dos desvios.")
        st.caption("Cálculo dinâmico por indicador. Requer 12 valores anteriores válidos; não indica contaminação.")

selected=sensors.loc[sensors["device_id"].astype(str).eq(chosen)].copy() if chosen else sensors.iloc[0:0].copy()
filtered=selected.iloc[0:0].copy()
if not selected.empty:
    selected=analyze(selected,window,threshold)
    with st.sidebar:
        recent_period = st.selectbox("Período dos sensores", ["Últimas 24h disponíveis", "Últimos 7 dias disponíveis", "Todo o retorno", "Escolher datas"], key="recent_period")
    latest_stamp = selected["data_hora"].max()
    if recent_period == "Escolher datas":
        with st.sidebar:
            period=st.date_input("Período — Brasília",value=(selected["data_hora"].min().date(),latest_stamp.date()),min_value=selected["data_hora"].min().date(),max_value=latest_stamp.date(),format="DD/MM/YYYY")
        if isinstance(period,(list,tuple)) and len(period)==2:
            start=pd.Timestamp(period[0],tz=BRASILIA)
            end=pd.Timestamp(period[1],tz=BRASILIA)+pd.Timedelta(days=1)
            filtered=selected.loc[selected["data_hora"].ge(start)&selected["data_hora"].lt(end)].copy()
    elif recent_period == "Todo o retorno":
        filtered=selected.copy()
    else:
        days = 1 if recent_period == "Últimas 24h disponíveis" else 7
        filtered=selected.loc[selected["data_hora"].ge(latest_stamp-pd.Timedelta(days=days))].copy()

forecast_frame = latest_forecast_series(p)

home,validation,detail,entries,method=st.tabs([
    "Visão geral", "Validação Histórica", "Sensor Individual", "Qualidade dos Dados", "Metodologia"
])
with home:
    st.subheader("Panorama epidemiológico", help="A classificação usa a última execução da visão operacional. A geração é a data em que o modelo produziu o resultado; a semana-alvo é o período estimado. Previsões reconstruídas e observados provisórios são identificados, sem substituição de ausentes por zero.")
    st.caption("Antecedência da previsão: 1 semana.")
    render_prediction(forecast_frame)
    if forecasts.empty:
        st.warning("Previsão indisponível nesta atualização. Os detalhes estão em Qualidade dos Dados.")
    elif forecast_missing:
        st.error("Campos ausentes: " + ", ".join(forecast_missing))
    elif forecast_frame.empty:
        st.warning("Previsão de uma semana indisponível na execução mais recente.")
    else:
        frame = forecast_frame.copy()
        if not frame.empty:
            last = frame.iloc[-1]
            horizon = int(last["horizonte"])
            weeks = st.selectbox("Semanas na linha do tempo", [12, 26, 52], key="forecast_weeks",
                                 help="A linha do tempo mantém as datas reais e abre nas semanas mais recentes desta execução.")
            chart_frame = frame.tail(weeks)
            paired = frame.dropna(subset=["observado", "previsto"])
            errors = paired["previsto"] - paired["observado"]
            if not paired.empty:
                a,b,c,d = st.columns(4)
                a.metric("Erro absoluto médio provisório", value(errors.abs().mean(), " casos"), help="Comparação apenas nas semanas com estimativa e observado provisório disponível. Pode mudar com a consolidação dos casos.")
                b.metric("Viés médio provisório", value(errors.mean(), " casos"), help="Estimativa menos observado provisório, nas semanas com ambos disponíveis.")
                c.metric("Semanas com comparação", str(len(paired)))
                d.metric("Observado provisório mais recente", value(paired.iloc[-1]["observado"]))
            else:
                st.caption("Casos observados indisponíveis nesta execução. A curva mostra as estimativas; MAE e viés aguardam dados observados.")

            fig=go.Figure()
            for field,label,color,dash in [("observado","Observado","#94a3b8","solid"),("previsto","Estimativa do modelo","#67c5da","solid"),("limiar_atencao","Limiar de atenção","#f59e0b","dot"),("limiar_alerta","Limiar principal","#ef4444","dash")]:
                if field == "observado":
                    if not chart_frame["observado"].notna().any():
                        continue
                    label = "Observado provisório"
                fig.add_trace(go.Scatter(x=chart_frame["inicio_semana_alvo"],y=chart_frame[field],name=label,line=dict(color=color,dash=dash,width=2),connectgaps=False))
            fig.update_yaxes(rangemode="tozero")
            chart_title = "Evolução de casos estimados e observados provisórios" if chart_frame["observado"].notna().any() else "Evolução das estimativas operacionais"
            fig.update_layout(title=chart_title,xaxis_title="Semana-alvo",yaxis_title="Casos",hovermode="x unified")
            show(fig, navigable=True, date_only=True)
            frame["erro_previsto_menos_observado"]=frame["previsto"]-frame["observado"]
            with st.expander("Conferir previsões • mais recentes primeiro"):
                table(frame,width="stretch",hide_index=True)
                export(frame,"previsoes_operacionais")


    st.divider()
    st.subheader("Entrada dos sensores")
    render_telemetry_summary(selected, filtered, LABELS, metrics=False)
    latest_cards(filtered)
    if filtered.empty:
        empty()
    else:

        fig=make_subplots(rows=4,cols=1,shared_xaxes=True,vertical_spacing=.10,subplot_titles=list(LABELS.values()))
        for row,(col,label) in enumerate(LABELS.items(),1):
            try:
                series=grouped_series(filtered,col,aggregation)
                chart_series = pd.DataFrame({"data_hora":series.index,col:series.values})
                if aggregation == "Original":
                    chart_series = break_line_at_gaps(chart_series,[col])
                fig.add_trace(go.Scatter(x=chart_series["data_hora"],y=chart_series[col],name=label,legendrank=row,mode="lines",line=dict(color=COLORS[col]),connectgaps=False),row=row,col=1)
            except DisplayRangeError as exc:
                st.info(f"{label}: {exc}")
            plotted = hide_edge_zeros(filtered, col)
            flagged=plotted.loc[plotted[col+"_desvio"] & plotted[col].notna()]
            fig.add_trace(go.Scatter(x=flagged["data_hora"] if not flagged.empty else [None],y=flagged[col] if not flagged.empty else [None],name="Alteração relevante",legendrank=5,legendgroup="alteracao_relevante",showlegend=row == 1,text=[label]*len(flagged),hovertemplate="%{text}: %{y}<br>%{x}<extra>Alteração relevante</extra>",mode="markers",marker=dict(color="#ef4444",size=7)),row=row,col=1)
            fig.update_yaxes(title_text=label,row=row,col=1, rangemode="tozero" if col=="ph_value" else "normal")
        fig.update_layout(height=1100,title="Evolução dos quatro sensores — escalas independentes",hovermode="x unified")
        fig.update_annotations(yshift=12, yanchor="bottom", font=dict(size=15))
        sensor_info = escape("Cada sensor tem seu próprio eixo vertical; alturas semelhantes não representam valores equivalentes. Pontos vermelhos sinalizam mudanças estatisticamente incomuns entre leituras, comparadas às mudanças anteriores do mesmo sensor: escore modificado com mediana e MAD, |M| > 3,5. Exige 12 diferenças anteriores válidas; com MAD zero ou intervalos inválidos, não há avaliação. Não indica contaminação. Método e referências estão na aba Metodologia.", quote=True)
        st.markdown(f'<div class="sensor-chart-heading"><h3>Evolução dos quatro sensores — escalas independentes</h3><details class="info-tip"><summary aria-label="Informações sobre escalas e alterações relevantes">ⓘ</summary><span class="info-content">{sensor_info}</span></details></div>', unsafe_allow_html=True)
        fig.update_xaxes(title_text="Horário (Brasília)",row=4,col=1)
        show(fig, sensor_overview=True)
        st.caption("Ao agrupar, a linha mostra a média de cada intervalo. O ponto vermelho marca uma leitura real com mudança estatisticamente incomum, mesmo que a linha mostre médias. Zeros nas pontas dos quatro sensores ficam ocultos na linha e nos marcadores; tabelas e cálculos preservam esses registros. Trechos sem leituras ficam interrompidos; na série original, a quebra ocorre quando o intervalo entre leituras supera 7min30s.")
with validation:
    st.subheader("Validação Histórica", help="Comparação retrospectiva com os casos observados da tabela de avaliação histórica. MAE, RMSE e viés medem erros em casos; não representam uma porcentagem de acurácia nem garantem desempenho futuro.")
    if historical_result.issue:
        st.warning("Avaliação histórica indisponível nesta atualização. " + historical_result.issue.message)
    elif historical_missing:
        st.warning("Campos ausentes na avaliação histórica: " + ", ".join(historical_missing))
    elif latest_forecast_series(historical).empty:
        st.info("Nenhuma avaliação histórica de uma semana disponível nesta execução.")
    else:
        history = latest_forecast_series(historical)
        start_date = history['inicio_semana_alvo'].min().strftime("%d/%m/%Y")
        end_date = history['inicio_semana_alvo'].max().strftime("%d/%m/%Y")
        st.markdown(f'<div class="telemetry-strip"><strong>Avaliação retrospectiva</strong><span>Série completa: {start_date} a {end_date}</span><span>Antecedência: 1 semana</span></div>', unsafe_allow_html=True)
        with st.expander("Como interpretar a Validação Histórica"):
            st.write("Compara estimativas com os casos observados de toda a série histórica disponível na última execução, com uma semana de antecedência. Os indicadores usam somente semanas com os dois valores válidos; zero observado continua válido.")
            st.caption("Os resultados descrevem o desempenho nesse período. Não representam percentual de acurácia nem garantem o desempenho das previsões operacionais da Visão geral.")
        scores = historical_metrics(history)
        if scores is None:
            st.info("Não há semanas com casos observados e estimados disponíveis para calcular os indicadores.")
        else:
            historical_cards = [
                ("Erro absoluto médio (MAE)", value(scores["mae"], " casos"), "Distância média entre estimativa e observado. Quanto menor, melhor."),
                ("Raiz do erro quadrático (RMSE)", value(scores["rmse"], " casos"), "Dá mais peso aos erros maiores. Quanto menor, melhor."),
                ("Viés médio", value(scores["bias"], " casos"), "Positivo: superestimação. Negativo: subestimação."),
                ("Semanas comparadas", str(scores["weeks"]), "Semanas com estimativa e observação válidas, incluindo zero observado."),
            ]
            cards = ''.join(f'<section class="sensor-card"><div class="sensor-name">{escape(label)}</div><div class="sensor-value-row"><strong>{escape(displayed)}</strong></div><div class="sensor-comparison">{escape(explanation)}</div></section>' for label, displayed, explanation in historical_cards)
            st.markdown('<div class="sensor-cards historical-cards">' + cards + '</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for field,label,color,dash in [
            ("observado", "Casos observados", "#94a3b8", "solid"),
            ("previsto", "Estimativa do modelo", "#67c5da", "solid"),
            ("limiar_atencao", "Limiar de atenção", "#f59e0b", "dot"),
            ("limiar_alerta", "Limiar de alerta", "#ef4444", "dash"),
        ]:
            fig.add_trace(go.Scatter(x=history["inicio_semana_alvo"], y=history[field],
                name=label, mode="lines+markers" if field in ("observado", "previsto") else "lines",
                marker=dict(size=4), line=dict(color=color, dash=dash, width=2), connectgaps=False))
        fig.update_layout(title="Casos observados × estimados — avaliação histórica",
                          xaxis_title="Semana-alvo", yaxis_title="Casos", hovermode="x unified", height=470)
        fig.update_yaxes(rangemode="tozero")
        show(fig, navigable=True, date_only=True)


with detail:
    if filtered.empty:
        empty()
    else:
        col=st.selectbox("Indicador principal",list(LABELS),format_func=LABELS.get)
        label=LABELS[col]
        st.subheader(f"{label} — análise individual")
        st.markdown(f'<div class="telemetry-strip"><strong>{escape(label)}</strong><span>Dispositivo: {escape(str(chosen))}</span><span>{filtered["data_hora"].min():%d/%m/%Y %H:%M} a {filtered["data_hora"].max():%d/%m/%Y %H:%M} (Brasília)</span></div>', unsafe_allow_html=True)
        values = filtered[col].dropna()
        current_stats = individual_statistics(filtered, col)
        comparison_context = (str(chosen), col, recent_period, str(period) if recent_period == "Escolher datas" else "")
        analyses = st.session_state.setdefault("individual_analyses", {})
        snapshot = advance_analysis(analyses.get(comparison_context), current_stats, sensor_result.attempted_at)
        analyses[comparison_context] = snapshot
        comparison_label = (
            "Primeira consulta dos sensores" if snapshot["compared_at"] == snapshot["update_id"]
            else "Comparação com a consulta anterior dos sensores"
        )
        card_specs = [("minimum", "Mínimo"), ("mean", "Média"), ("maximum", "Máximo"), ("std", "Desvio-padrão")]
        cards = []
        for key, title in card_specs:
            current = current_stats[key]
            difference = snapshot["changes"][key]
            tone = "up" if difference > 0 else "down" if difference < 0 else "neutral"
            arrow = "↑" if difference > 0 else "↓" if difference < 0 else "="
            capsule = f'<span class="sensor-change {tone}">{arrow} {value(abs(difference))}</span>'
            displayed = value(current, " °C" if col == "temperature_value" else "")
            cards.append(f'<section class="sensor-card"><div class="sensor-name">{title} de {escape(label)}</div><div class="sensor-value-row"><strong>{escape(displayed)}</strong>{capsule}</div><div class="sensor-comparison">{escape(comparison_label)}</div></section>')
        st.markdown('<div class="sensor-cards">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
        with st.expander("Como interpretar esta análise"):
            st.write("O histórico mostra os valores do indicador ao longo do tempo. O gráfico diário mostra quantos registros válidos chegaram no recorte consultado. Aumento de registros indica mais registros disponíveis, não melhora da água; aumento do valor do sensor deve ser interpretado no histórico.")
            st.write("Os cards usam todas as leituras numéricas do período, inclusive zeros. As cápsulas comparam cada estatística com a análise da consulta anterior nesta sessão, para o mesmo dispositivo, indicador e filtro. A atualização automática ocorre a cada 30 segundos quando ligada. Na primeira análise, a própria consulta inicializa a referência e a cápsula fica em = 0,00. Sem valores válidos para comparar, a cápsula também fica neutra e o valor principal permanece ausente. Verde significa aumento, vermelho redução e cinza igualdade; não significa melhora ou piora da água.")
            st.caption("Atualizar a consulta não garante uma nova leitura do sensor. Se os dados permanecerem iguais, a variação será = 0,00. Alterar o indicador ou o filtro inicia uma referência independente; outras interações não apagam a variação da última consulta.")
        if values.empty:
            st.info("O indicador selecionado não possui valores numéricos válidos neste período.")
        elif values.nunique() == 1:
            st.info(f"Valor constante no período: {value(values.iloc[0])} em {len(values)} leituras válidas. A linha reta representa os dados recebidos; não comprova precisão, calibração ou funcionamento do sensor.")
        else:
            st.caption(f"{len(values)} leituras válidas • {values.nunique()} valores distintos • amplitude: {value(values.max() - values.min())}.")
        detail_chart = break_line_at_gaps(filtered,[col])
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=detail_chart["data_hora"],y=detail_chart[col],name=label,mode="lines",line=dict(color=COLORS[col],width=2),connectgaps=False))
        fig.update_layout(title=f"Histórico de {label}",xaxis_title="Horário (Brasília)",yaxis_title=label,hovermode="x unified")
        if col == "ph_value":
            fig.update_yaxes(rangemode="tozero")
        show(fig)
        st.caption("A linha mostra os valores recebidos, sem faixas ou curvas adicionais. Zeros nas pontas ficam ocultos somente na linha; os registros permanecem nos cards e na contagem diária. Lacunas acima de 7min30s interrompem a linha.")
        if len(filtered) == 1:
            st.info("Há apenas um registro no período; uma linha exige ao menos dois pontos. Consulte o valor nos cards.")
        st.subheader("Análises registradas por dia")
        try:
            daily_counts = daily_summary(filtered,col)
            daily_fig = go.Figure(go.Scatter(
                x=daily_counts["data_hora"], y=daily_counts["leituras_validas"],
                name="Análises válidas", mode="lines+markers",
                line=dict(color=COLORS[col],width=2), marker=dict(size=6), connectgaps=False,
            ))
            daily_fig.update_layout(title=f"{label} — quantidade de análises por dia",xaxis_title="Dia (Brasília)",yaxis_title="Análises registradas",height=350)
            daily_fig.update_yaxes(rangemode="tozero",dtick=1 if daily_counts["leituras_validas"].max() <= 10 else None)
            show(daily_fig,date_only=True)
            st.caption("Cada análise corresponde a um registro com valor numérico válido do indicador, inclusive zero. Atualizações da tela a cada 30 segundos não contam como novas análises. A contagem usa apenas os registros do dispositivo e período selecionados retornados pela consulta (até 1.000 no total); dias parciais e lacunas não comprovam falha do sensor. Datas agrupadas pelo dia de Brasília.")
        except DisplayRangeError as exc:
            st.warning(str(exc))
        st.subheader("Análises e Comparação com a Média")
        comparison_table = filtered[["data_hora", col, col+"_media"]].copy()
        comparison_table["Variação"] = comparison_table[col] - comparison_table[col+"_media"]
        comparison_table["Posição em relação à média"] = np.select(
            [comparison_table["Variação"].isna(), comparison_table["Variação"].gt(0), comparison_table["Variação"].lt(0)],
            ["Sem referência", "Acima", "Abaixo"], default="Igual",
        )
        comparison_table = comparison_table.rename(columns={col:LABELS[col], col+"_media":"Média anterior"}).sort_values("data_hora",ascending=False)
        table(comparison_table,width="stretch",hide_index=True)
        st.caption(f"A média usa até {window} leituras anteriores válidas deste dispositivo, com mínimo de 12, sem incluir a leitura da própria linha. A variação é o valor menos essa média, na unidade do indicador; não é percentual nem a variação entre atualizações dos cards. Valores ausentes não viram zero. Estar acima ou abaixo não indica risco ou funcionamento correto do sensor.")
        export(comparison_table,"analises_comparacao_media")
with entries:
    st.subheader("Qualidade dos Dados")
    with st.container(border=True):
        st.subheader("Conexão com o Banco de Dados")
        successful_reads = [result for result in source_results if result.issue is None and result.fetched_at is not None]
        if len(successful_reads) == len(source_results):
            st.success("Conectado — as três fontes responderam às consultas de leitura.")
        elif successful_reads:
            st.warning("Acesso parcial — o banco respondeu, mas uma ou mais fontes apresentaram falha.")
        else:
            st.error("Acesso indisponível — nenhuma consulta de leitura foi concluída nesta atualização.")
        connection_columns = st.columns(2)
        connection_columns[0].metric("Fontes consultadas com sucesso", f"{len(successful_reads)} de {len(source_results)}")
        last_read = latest_success_at(source_results)
        completed = last_read.astimezone(BRASILIA).strftime("%d/%m/%Y %H:%M:%S") if last_read else "Indisponível"
        connection_columns[1].metric("Última atualização dos dados (Brasília)", completed)
        st.caption("Sensores, previsões operacionais e validação histórica são consultados no mesmo ciclo, com cache de até 30 segundos. O horário indica o fim da última consulta bem-sucedida do ciclo. A data da leitura e a geração da previsão aparecem nas respectivas seções.")
        st.markdown("#### Fontes Consultadas")
        st.caption("São três conjuntos de dados no mesmo banco: sensores, previsões operacionais e avaliação histórica. Não são três bancos nem três sensores.")
        for label, result in (("Sensores", sensor_result), ("Previsões operacionais", forecast_result), ("Avaliação histórica", historical_result)):
            if result.issue:
                st.error(f"{label}: {result.issue.message}")
            else:
                st.write(f"{label}: {len(result.frame)} registros • {result.elapsed_ms} ms")
                if result.frame.empty:
                    st.info(f"{label}: consulta concluída sem registros visíveis para o usuário configurado.")
        if missing and not sensor_error:
            st.error("Colunas ausentes em sensores: " + ", ".join(missing))
        if forecast_missing and not forecast_error:
            st.error("Colunas ausentes em previsões: " + ", ".join(forecast_missing))
        if invalid:
            st.warning(f"{invalid} registros de sensores com horário inválido ficaram fora da análise.")
        if forecast_invalid:
            st.warning(f"{forecast_invalid} previsões com data ou horizonte fora do contrato ficaram fora da análise.")

    render_telemetry_summary(filtered, filtered, LABELS, show_status=False)
    st.subheader("Últimas Leituras")
    st.caption("Registros do dispositivo e período selecionados, do mais novo para o mais antigo. A consulta retorna até 1.000 registros no total, antes dos filtros. O farol indica preenchimento: verde sem ausências ou zeros, amarelo com zero e vermelho com ausência ou valor inválido. Não é classificação da qualidade da água.")
    if filtered.empty:
        st.info("Nenhuma leitura disponível no recorte selecionado.")
    else:
        quality = reading_quality(filtered)
        quality_columns = ["id", "device_id", "data_hora", *LABELS, "Farol", "Motivo"]
        output = quality.reindex(columns=quality_columns).sort_values("data_hora",ascending=False)
        output = output.rename(columns={"id":"ID", "device_id":"Dispositivo"})
        table(output,width="stretch",hide_index=True)
        export(output,"leituras_esp32")


with method:
    st.subheader("Como interpretar")
    st.subheader("Critério dos Pontos Vermelhos")
    st.write("A mesma regra vale para os quatro sensores, separadamente: diferença entre leituras consecutivas, comparada à mediana e ao desvio absoluto mediano (MAD) das diferenças anteriores. Ponto vermelho quando |M| > 3,5. Referência padrão de 48 diferenças, mínimo de 12 válidas; a diferença atual fica fora da referência. Lacunas acima de 7min30s e horários duplicados não geram diferenças válidas. Com MAD zero ou histórico insuficiente, a avaliação fica indisponível.")
    st.write("Adaptação exploratória para mudanças temporais do escore modificado de Iglewicz–Hoaglin. Não é limite sanitário nem norma específica de sensores. Pequenas mudanças podem ser atípicas em séries muito estáveis; resolução, calibração e desempenho precisam de validação por sensor. Não detectar mudança não comprova normalidade.")
    st.markdown("Referências: [NIST — escore modificado e limiar 3,5](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) e [USGS — monitoramento e calibração](https://pubs.usgs.gov/tm/2006/tm1D3/). A janela causal e a aplicação às diferenças são escolhas deste protótipo, ainda sem validação de sensibilidade e falsos positivos em campo.")


    with st.expander("Como relacionar telemetria e classificação"):
        st.write("A classificação destacada vem da execução mais recente da visão operacional disponível no banco. Sua data de referência é informada no farol. Os sensores descrevem a água no período escolhido e são analisados separadamente. Uma alteração no sensor não altera a classificação epidemiológica.")
        st.caption("Chuva, mapa de localização e explicações de variáveis ainda não estão disponíveis nesta consulta.")

    st.markdown("""
- Cada indicador usa seu próprio histórico e sua própria escala. Não há comparação direta entre pH, turbidez, TDS e temperatura.
- Mínimo, média, máximo e desvio-padrão se referem ao indicador e período selecionados; ausentes são excluídos.
- A referência de uma leitura usa apenas registros anteriores: até N registros, mínimo de 12 valores válidos. A janela é por registros, não por horas.
- A faixa histórica de média ± 3,5 desvios-padrão é apenas descritiva dos níveis. Pontos vermelhos usam outra regra: M = 0,6745 × (diferença atual − mediana das diferenças anteriores) / MAD anterior, com |M| > 3,5. Não é percentual nem limite sanitário.
- Sem 12 diferenças anteriores válidas ou com MAD zero, a avaliação da mudança fica indisponível. Isso não é uma leitura normal nem evidência de ausência de alteração.
- A referência é calculada antes do filtro de datas, usando o histórico retornado pelo backend.
- Horários de leitura, consulta e geração são exibidos em Brasília (UTC−03). Filtros e resumos diários de sensores seguem o calendário de Brasília. Datas de referência das previsões mantêm o dia informado pela fonte.
- Integração visual não significa que os sensores diagnosticam leptospirose ou alimentaram o modelo histórico.
- A visão operacional fornece estimativas do modelo Poisson, data de geração, semana-alvo e tipo de previsão. Resultados reconstruídos não são previsões produzidas no passado em tempo real.
- A aba Validação histórica usa a tabela de avaliação anterior, sua série completa e indicadores com antecedência fixa de uma semana. Essa avaliação retrospectiva é separada das estimativas operacionais.
- Observados desta fonte são provisórios; quando ausentes, não há curva de observados nem métricas de comparação. Ausência não significa zero casos.
- Chuva, localização e explicações da IA dependem de carregadores específicos ainda não fornecidos.
- Falhas de carregamento não são substituídas por dados fictícios. Somente as linhas retornadas pelas consultas entram na análise.
""")
    st.latex(r"z_t=\frac{x_t-\mu_{\mathrm{anterior}}}{s_{\mathrm{anterior}}}")
st.divider()
