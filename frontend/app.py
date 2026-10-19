"""Dashboard integrado do prototipo WBE-IoT."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import build_engine, database_url, load_predictions, load_sensor_readings
from domain import level_label

st.set_page_config(
    page_title="Vigilância WBE-IoT",
    page_icon="🌊",
    layout="wide",
)


@st.cache_resource
def get_engine():
    return build_engine(database_url(st.secrets))


@st.cache_data(ttl=60)
def predictions_data():
    return load_predictions(get_engine())


@st.cache_data(ttl=30)
def sensor_data():
    return load_sensor_readings(get_engine())


st.title("Vigilância epidemiológica urbana — WBE-IoT")
st.caption(
    "Protótipo acadêmico: previsão epidemiológica e telemetria física são "
    "integradas na interface, mas avaliadas como módulos distintos."
)

try:
    predictions = predictions_data()
    sensors = sensor_data()
except Exception as exc:
    st.error("Não foi possível consultar o banco. Confira o segredo TCC_DB_URL.")
    with st.expander("Detalhe técnico"):
        st.code(type(exc).__name__)
    st.stop()

tab_prediction, tab_iot, tab_method = st.tabs(
    ["Previsão epidemiológica", "Telemetria IoT", "Metodologia"]
)

with tab_prediction:
    horizon = st.segmented_control(
        "Horizonte de previsão", options=[1, 2], default=1,
        format_func=lambda value: f"t+{value} semana{'s' if value == 2 else ''}",
    )
    frame = predictions.loc[predictions["horizonte"].eq(horizon)].copy()
    latest = frame.iloc[-1]
    level = str(latest["nivel_previsto"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Última previsão do teste", f"{latest['previsto']:.2f} casos")
    c2.metric("Nível", level_label(level))
    c3.metric("Atenção", f"≥ {latest['limiar_atencao']:.0f} casos")
    c4.metric("Limiar principal", f"≥ {latest['limiar_alerta']:.0f} casos")
    target_date = latest["inicio_semana_alvo"].strftime("%d/%m/%Y")
    st.caption(
        f"Semana-alvo da última previsão: {target_date}. "
        "Resultados retrospectivos do holdout de 2024; não representam uma "
        "previsão produzida na data atual."
    )

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["inicio_semana_alvo"], y=frame["observado"],
            name="Observado", line={"color": "#e5e7eb", "width": 2.5}
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame["inicio_semana_alvo"], y=frame["previsto"],
            name="Poisson congelado", line={"color": "#2563eb", "width": 3}
        )
    )
    figure.add_hline(
        y=float(latest["limiar_atencao"]), line_dash="dot",
        line_color="#f59e0b", annotation_text="Atenção"
    )
    figure.add_hline(
        y=float(latest["limiar_alerta"]), line_dash="dash",
        line_color="#dc2626", annotation_text="Limiar principal"
    )
    figure.update_layout(
        title=f"Casos semanais — t+{horizon}",
        xaxis_title="Semana-alvo", yaxis_title="Casos", hovermode="x unified"
    )
    st.plotly_chart(figure, use_container_width=True)
    st.info(
        "O nível de atenção (2 a menos de 4) é exploratório. O limiar principal "
        "do protótipo permanece em 4 casos e foi pré-especificado antes da "
        "abertura do teste de 2024."
    )

with tab_iot:
    if sensors.empty:
        st.warning("Ainda não há leituras físicas disponíveis.")
    else:
        latest_sensor = sensors.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("pH", f"{latest_sensor['ph_value']:.2f}")
        c2.metric("Turbidez", f"{latest_sensor['turbidity_value']:.2f}")
        c3.metric("TDS", f"{latest_sensor['tds_value']:.2f}")
        c4.metric("Temperatura", f"{latest_sensor['temperature_value']:.2f} °C")
        selected_device = st.selectbox(
            "Dispositivo", sorted(sensors["device_id"].dropna().unique())
        )
        device = sensors.loc[sensors["device_id"].eq(selected_device)]
        long = device.melt(
            id_vars=["data_hora"],
            value_vars=[
                "ph_value", "turbidity_value", "tds_value", "temperature_value"
            ],
            var_name="indicador", value_name="valor",
        )
        chart = px.line(long, x="data_hora", y="valor", facet_row="indicador")
        chart.update_yaxes(matches=None)
        chart.update_layout(height=750, title="Histórico recente dos sensores")
        st.plotly_chart(chart, use_container_width=True)
        st.warning(
            "Estas leituras descrevem condições físico-químicas da amostra. "
            "Elas não detectam diretamente a bactéria e não alimentaram o "
            "modelo epidemiológico histórico."
        )

with tab_method:
    st.subheader("Como interpretar o protótipo")
    st.markdown(
        """
        - **Modelo epidemiológico:** Poisson regularizado, treinado com clima e sazonalidade.
        - **Horizontes:** uma e duas semanas à frente.
        - **Limiar principal do protótipo:** previsão de pelo menos 4 casos semanais, pré-especificado antes da avaliação de 2024.
        - **Avaliação histórica:** as previsões atualmente exibidas pertencem ao holdout temporal de 2024, não a uma execução em tempo real.
        - **IoT físico:** mede pH, turbidez, TDS e temperatura e comprova o fluxo sensor → MQTT → Supabase.
        - **Limite:** integração visual não significa que os sensores diagnosticam leptospirose.
        """
    )
    st.caption("Uso acadêmico. Não constitui sistema clínico ou alerta oficial de saúde pública.")
