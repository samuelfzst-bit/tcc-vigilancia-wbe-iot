"""Cálculos puros do dashboard; preserva a referência anterior por registros."""
from __future__ import annotations

import math
from numbers import Integral

import numpy as np
import pandas as pd

LABELS = {
    "ph_value": "pH",
    "turbidity_value": "Turbidez (leitura experimental)",
    "tds_value": "TDS (leitura experimental)",
    "temperature_value": "Temperatura (°C)",
}
MIN_HISTORY = 12
AGGREGATIONS = {"Original": None, "5 minutos": "5min", "15 minutos": "15min", "30 minutos": "30min", "60 minutos": "60min"}
GAP_TOLERANCE = pd.Timedelta(minutes=7, seconds=30)
MAX_DISPLAY_BINS = 20_000


class DisplayRangeError(ValueError):
    """O gráfico requer um recorte menor; não altera leituras ou estatísticas."""


def prepare(frame):
    required = ["device_id", "data_hora", *LABELS]
    if frame.empty:
        return pd.DataFrame(columns=required), [], 0
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        return pd.DataFrame(columns=required), missing, 0
    result = frame.copy()
    result["data_hora"] = pd.to_datetime(result["data_hora"], errors="coerce", utc=True)
    invalid = int(result["data_hora"].isna().sum())
    result = result.dropna(subset=["data_hora"])
    for col in LABELS:
        result[col] = pd.to_numeric(result[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return result.sort_values("data_hora"), [], invalid


def analyze(frame, window, threshold=3.5):
    if isinstance(window, bool) or not isinstance(window, Integral) or not MIN_HISTORY <= window <= 96:
        raise ValueError("A janela deve ter entre 12 e 96 registros anteriores.")
    if not math.isfinite(threshold) or not 2 <= threshold <= 4:
        raise ValueError("O limiar deve estar entre 2 e 4.")
    result = frame.sort_values("data_hora").copy()
    elapsed = result["data_hora"].diff()
    consecutive = elapsed.gt(pd.Timedelta(0)) & elapsed.le(GAP_TOLERANCE)
    for col in LABELS:
        rolling = result[col].shift(1).rolling(window, min_periods=MIN_HISTORY)
        result[col + "_media"] = rolling.mean()
        result[col + "_std"] = rolling.std().replace(0, np.nan)
        result[col + "_z"] = (result[col] - result[col + "_media"]) / result[col + "_std"]
        # Adaptação causal do escore modificado de Iglewicz–Hoaglin (NIST):
        # aplicado às diferenças, para detectar mudanças e não novos patamares.
        changes = result[col].diff().where(consecutive)
        history = changes.shift(1).rolling(window, min_periods=MIN_HISTORY)
        center = history.median()
        mad = history.apply(lambda values: np.nanmedian(np.abs(values - np.nanmedian(values))), raw=True).replace(0, np.nan)
        result[col + "_change_z"] = 0.6745 * (changes - center) / mad
        result[col + "_desvio"] = result[col + "_change_z"].abs().gt(threshold)
    result["indicadores_com_desvio"] = result[[c + "_desvio" for c in LABELS]].sum(axis=1)
    return result


def reading_quality(frame):
    """Farol de preenchimento por registro; zero não é convertido em ausência."""
    result = frame.copy()
    values = frame.reindex(columns=list(LABELS)).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    missing = values.isna()
    zero = values.eq(0)
    result["Farol"] = np.select([missing.any(axis=1), zero.any(axis=1)],
                                ["🔴", "🟡"], default="🟢")
    result["Motivo"] = ["; ".join(
        (["Ausente/inválido: " + ", ".join(LABELS[c] for c in LABELS if missing.loc[idx, c])] if missing.loc[idx].any() else [])
        + (["Zero: " + ", ".join(LABELS[c] for c in LABELS if zero.loc[idx, c])] if zero.loc[idx].any() else [])
    ) or "100% preenchido" for idx in values.index]
    return result


def individual_statistics(frame, col):
    values = frame[col].dropna()
    return {"minimum": values.min(), "mean": values.mean(), "maximum": values.max(), "std": values.std()}


def advance_analysis(previous, current, update_id):
    """Uma comparação por consulta; interações não apagam a variação exibida."""
    if previous is not None and previous["update_id"] == update_id:
        return previous
    baseline = previous["values"] if previous is not None else current
    changes = {key: round(float(value - baseline[key]), 2)
               if pd.notna(value) and pd.notna(baseline[key]) else 0.
               for key, value in current.items()}
    return {"update_id": update_id, "compared_at": previous["update_id"] if previous is not None else update_id,
            "values": current.copy(), "changes": changes}


def check_display_range(dates, frequency):
    valid = dates.dropna()
    if len(valid) > 1:
        seconds = (valid.max().to_pydatetime() - valid.min().to_pydatetime()).total_seconds()
        bins = seconds / pd.Timedelta(frequency).total_seconds() + 2
        if bins > MAX_DISPLAY_BINS:
            raise DisplayRangeError("Este intervalo gera muitos pontos. Escolha um período menor ou um agrupamento maior.")


def hide_edge_zeros(frame, col):
    """Oculta zeros nas bordas dos gráficos; preserva dados e zeros internos."""
    result = frame.copy()
    values = result[col]
    removable = values.eq(0)
    # Valores ausentes não devem transformar zeros internos em bordas.
    anchors = values.notna() & ~removable
    if anchors.any():
        positions = np.flatnonzero(anchors.to_numpy())
        edge = np.arange(len(result)) < positions[0]
        edge |= np.arange(len(result)) > positions[-1]
        result.loc[removable & edge, col] = np.nan
    else:
        result.loc[removable, col] = np.nan
    return result


def grouped_series(frame, col, aggregation):
    if aggregation not in AGGREGATIONS:
        raise ValueError("Agrupamento desconhecido.")
    ordered = frame.sort_values("data_hora", kind="stable")
    series = hide_edge_zeros(ordered, col).set_index("data_hora")[col].copy()
    frequency = AGGREGATIONS[aggregation]
    if frequency:
        check_display_range(pd.Series(series.index), frequency)
        series = series.resample(frequency).mean()
    return series


def break_line_at_gaps(frame, columns):
    """Insere apenas pontos visuais vazios; não modifica a origem nem os cálculos."""
    source = frame.sort_values("data_hora", kind="stable").copy()
    for col in columns:
        if col in LABELS and col + "_desvio" in source:
            source = hide_edge_zeros(source, col)
    result = source[["data_hora", *columns]].copy()
    gaps = result["data_hora"].diff().gt(GAP_TOLERANCE)
    if not gaps.any():
        return result
    breaks = result.loc[gaps].copy()
    breaks["data_hora"] = result["data_hora"].shift(1).loc[gaps] + pd.Timedelta(minutes=5)
    for col in columns:
        breaks[col] = np.nan
    return pd.concat([result, breaks], ignore_index=True).sort_values("data_hora", kind="stable")


def daily_summary(frame, col):
    check_display_range(frame["data_hora"], "1D")
    daily = frame.set_index("data_hora").resample("1D").agg(
        minimo=(col, "min"), media=(col, "mean"), maximo=(col, "max"),
        leituras_validas=(col, "count"), analisaveis=(col + "_change_z", "count"),
        sinalizacoes=(col + "_desvio", "sum"),
    ).reset_index()
    daily["percentual_sinalizado"] = daily["sinalizacoes"].div(daily["analisaveis"].replace(0, np.nan)) * 100
    return daily


REQUIRED_FORECASTS = ["horizonte", "inicio_semana_alvo", "observado", "previsto",
                      "nivel_previsto", "limiar_atencao", "limiar_alerta"]
LEVELS = {
    "normal": ("Normal", "Dentro da faixa de referência do modelo", "normal"),
    "atencao": ("Atenção", "Resultado na faixa exploratória de atenção", "attention"),
    "alerta": ("Alerta", "Resultado no nível de alerta do modelo", "alert"),
}


def prepare_forecasts(frame):
    """Normaliza uma cópia para as duas apresentações da previsão."""
    missing = sorted(set(REQUIRED_FORECASTS) - set(frame.columns))
    if missing:
        return pd.DataFrame(columns=REQUIRED_FORECASTS), missing
    result = frame.copy()
    result["inicio_semana_alvo"] = pd.to_datetime(result["inicio_semana_alvo"], errors="coerce", utc=True)
    for col in ("horizonte", "observado", "previsto", "limiar_atencao", "limiar_alerta"):
        result[col] = pd.to_numeric(result[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if "status_observado" in result:
        unavailable = result["status_observado"].astype("string").str.strip().str.lower().eq("indisponivel").fillna(False)
        result.loc[unavailable, "observado"] = np.nan
    result = result.dropna(subset=["inicio_semana_alvo", "horizonte"])
    # O contrato SQL existente permite somente horizontes de uma ou duas semanas.
    result = result.loc[result["horizonte"].isin((1, 2))]
    return result.sort_values("inicio_semana_alvo"), []

def forecast_state(row):
    """Nunca interpreta uma previsão ausente ou inconsistente como normal."""
    predicted, attention, alert = (row.get(k) for k in ("previsto", "limiar_atencao", "limiar_alerta"))
    if any(pd.isna(v) for v in (predicted, attention, alert)) or not 0 <= attention < alert or predicted < 0:
        return "Indisponível", "Previsão ou limiares ausentes / inválidos", "unavailable"
    expected = "alerta" if predicted >= alert else "atencao" if predicted >= attention else "normal"
    stored = str(row.get("nivel_previsto", "")).strip().lower()
    if stored != expected:
        return "Revisar resultado", "A classificação retornada diverge dos limiares ou não é reconhecida", "unavailable"
    return LEVELS[stored]

def latest_forecast_series(frame):
    """Horizonte de uma semana da última execução, sem fallback para duas semanas."""
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    if "criado_em" in result and "execucao_id" in result:
        dates = pd.to_datetime(result["criado_em"], errors="coerce", utc=True)
        if dates.notna().any():
            latest_id = result.loc[dates.idxmax(), "execucao_id"]
            result = result.loc[result["execucao_id"].eq(latest_id)]
    usable = result.dropna(subset=["inicio_semana_alvo", "horizonte"])
    if usable.empty:
        return result.iloc[:0]
    return usable.loc[usable["horizonte"].eq(1)].sort_values("inicio_semana_alvo")


def telemetry_summary(frame, now=None):
    if frame.empty:
        return None
    dates = frame["data_hora"].dropna().sort_values()
    if dates.empty:
        return None
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    delay = now - dates.iloc[-1]
    future = delay.total_seconds() < 0
    minutes = max(0, delay.total_seconds() / 60)
    age = f"{int(minutes)} min" if minutes < 60 else f"{int(minutes / 60)} h" if minutes < 1440 else f"{int(minutes / 1440)} dias"
    return dict(latest=dates.iloc[-1], age=age,
                status="Horário futuro: verificar" if future else "Leitura recente" if minutes <= 10 else "Leitura desatualizada",
                tone="unavailable" if future else "normal" if minutes <= 10 else "attention",
                gaps=int(dates.diff().gt(pd.Timedelta(minutes=7, seconds=30)).sum()))


def historical_metrics(frame):
    """Erros nas semanas com pares válidos, sem inventar acurácia percentual."""
    pairs = frame.dropna(subset=["observado", "previsto"])
    if pairs.empty:
        return None
    errors = pairs["previsto"] - pairs["observado"]
    return dict(weeks=len(pairs), mae=float(errors.abs().mean()),
                rmse=float(np.sqrt(errors.pow(2).mean())), bias=float(errors.mean()))
