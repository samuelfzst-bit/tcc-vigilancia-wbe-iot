"""Apresentação e indicadores locais; não abre conexões nem modifica dados."""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from .analytics import forecast_state, telemetry_summary
from .query_service import BRASILIA


def apply_style():
    st.markdown("<style>" + Path(__file__).with_name("dashboard.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)


def render_update_status(label, tone, detail, *, paused=False):
    safe_tone = tone if tone in ("normal", "attention", "unavailable") else "unavailable"
    suffix = " • Automático pausado" if paused else ""
    st.markdown(
        f'<div class="update-status {safe_tone}" title="{escape(detail, quote=True)}" '
        f'role="status" aria-live="polite"><span class="update-dot" aria-hidden="true"></span>'
        f'{escape(label + suffix)}</div>', unsafe_allow_html=True,
    )


def number(value, decimals=2):
    return "—" if pd.isna(value) else f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def render_prediction(frame):
    if frame.empty:
        st.markdown('<section class="signal-card unavailable"><p>Classificação epidemiológica</p><h2>Sem resultado disponível</h2><p>Confira a situação das consultas.</p></section>', unsafe_allow_html=True)
        return
    row = frame.iloc[-1]
    title, explanation, tone = forecast_state(row)
    week = row["inicio_semana_alvo"].strftime("%d/%m/%Y")
    kind = str(row.get("tipo_previsao", "")).strip().lower()
    reconstructed = kind == "reconstruida"
    past = row["inicio_semana_alvo"] < pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=14)
    provenance = f"Estimativa operacional para a semana de {week}."
    if reconstructed:
        provenance += " Série reconstruída com os dados disponibilizados na execução; não foi emitida em tempo real na semana-alvo."
    elif past:
        provenance += " A semana-alvo já passou; este resultado não representa o risco atual."
    published = pd.to_datetime(row.get("gerado_em", row.get("criado_em")), errors="coerce", utc=True)
    local = published.tz_convert(BRASILIA) if pd.notna(published) else None
    display_date = f"Gerado em {local:%d/%m/%Y %H:%M:%S} (Brasília)" if local is not None else "Data de geração indisponível"
    reference = f"Semana prevista: {week}" + (" • Reconstruída" if reconstructed else "")
    climate_limit = pd.to_datetime(row.get("data_limite_clima"), errors="coerce", utc=True)
    climate_note = "" if pd.isna(climate_limit) else f" Dados climáticos disponíveis até {climate_limit:%d/%m/%Y}."
    observed_note = " Casos observados desta fonte são provisórios quando disponíveis; valores ausentes não são zero."
    info = escape(f"{provenance}{climate_note}{observed_note} Horizonte da estimativa: {int(row['horizonte'])} semana(s). Modelo Poisson; classificação pelos limiares retornados pelo banco. Não é alerta oficial.", quote=True)
    lamps = "".join(f'<span class="signal-lamp {color} {"lit" if tone == color else ""}" title="{label}"></span>'
                    for color, label in (("normal", "Normal"), ("attention", "Atenção"), ("alert", "Alerta")))
    st.markdown(f'''<section class="signal-card {tone}" aria-label="Classificação epidemiológica: {escape(title)}">
        <div class="signal-label">Classificação epidemiológica <details class="info-tip"><summary aria-label="Informações sobre a classificação">ⓘ</summary><span class="info-content">{info}</span></details></div>
        <div class="signal-lights" aria-hidden="true">{lamps}</div>
        <h2>{escape(title)}</h2><p class="signal-explanation">{escape(explanation)}</p>
        <p class="signal-reference">{display_date}<br><small>{reference}</small></p>
        <div class="signal-evidence"><div><span>Casos estimados</span><strong>{number(row['previsto'])}</strong></div>
        <div><span>Atenção a partir de</span><strong>{number(row['limiar_atencao'])}<small> casos</small></strong></div>
        <div><span>Alerta a partir de</span><strong>{number(row['limiar_alerta'])}<small> casos</small></strong></div></div>
        </section>''', unsafe_allow_html=True)


def render_telemetry_summary(selected, filtered, labels, metrics=True, *, show_status=True):
    if show_status:
        readings_for_status = selected if metrics else filtered
        summary = telemetry_summary(readings_for_status)
        if summary is None:
            st.info("Sem telemetria disponível. Confira a conexão e selecione um dispositivo.")
            return
        device = escape(str(readings_for_status.iloc[-1]["device_id"]))
        stamp = summary["latest"].tz_convert(BRASILIA).strftime("%d/%m/%Y %H:%M:%S")
        st.markdown(f'<div class="telemetry-strip {summary["tone"]}"><strong>{summary["status"]}</strong><span>Dispositivo: {device}</span><span>Última leitura do período: {stamp} (Brasília)</span><span>Idade da leitura: {summary["age"]}</span></div>', unsafe_allow_html=True)
    if filtered.empty or not metrics:
        return
    readings = len(filtered)
    valid = int(filtered[list(labels)].notna().sum().sum())
    flagged = int(filtered["indicadores_com_desvio"].gt(0).sum())
    gaps = telemetry_summary(filtered)["gaps"]
    cells = st.columns(4)
    cells[0].metric("Leituras no recorte", f"{readings:,}".replace(",", "."), help="Até 1.000 registros na consulta atual, antes do filtro de dispositivo e período.")
    cells[1].metric("Campos não nulos", number(100 * valid / (readings * len(labels)), 1) + "%", help="Campos numéricos preenchidos entre os quatro indicadores; não mede cobertura de envios nem calibração.")
    cells[2].metric("Mudanças estatisticamente atípicas", str(flagged), help="Leituras com pelo menos uma mudança que atende ao critério robusto entre leituras. Não equivale a risco sanitário.")
    cells[3].metric("Lacunas entre envios", str(gaps), help="Intervalos acima de 7min30s, tolerância para o envio esperado a cada 5 minutos. Não contabiliza lacunas fora do recorte.")
