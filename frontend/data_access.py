"""Consultas somente leitura para o dashboard Streamlit."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def database_url(streamlit_secrets=None) -> str:
    value = os.getenv("TCC_DB_URL")
    if not value and streamlit_secrets is not None:
        value = streamlit_secrets.get("TCC_DB_URL")
    if not value or not value.startswith(
        ("postgresql+psycopg://", "postgresql://", "postgres://")
    ):
        raise RuntimeError(
            "Defina TCC_DB_URL nos segredos do Streamlit ou no ambiente do servidor."
        )
    # O projeto instala psycopg 3. Tornar o driver explícito evita que o
    # SQLAlchemy tente importar o psycopg2 quando a URI vem do Supabase.
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


def build_engine(url: str) -> Engine:
    return create_engine(
        url, pool_pre_ping=True, pool_recycle=300,
        pool_size=2, max_overflow=0, pool_timeout=10,
        connect_args={"connect_timeout": 10},
    )


def load_predictions(engine: Engine) -> pd.DataFrame:
    """Última execução operacional publicada, sem fallback para o holdout histórico."""
    query = text(
        """
        with ultima_execucao as (
            select execucao_id
            from public.tcc_previsoes_operacionais_dashboard
            group by execucao_id
            order by max(gerado_em) desc, execucao_id desc
            limit 1
        )
        select
            inicio_semana_alvo,
            inicio_semana_t,
            horizonte,
            observado_provisorio as observado,
            status_observado,
            previsto,
            nivel_previsto,
            limiar_atencao,
            limiar_alerta,
            tipo_previsao,
            modelo,
            versao_modelo,
            execucao_id,
            gerado_em as criado_em,
            gerado_em,
            data_corte,
            data_limite_clima,
            origem_dados_climaticos,
            clima_essencial_completo
        from public.tcc_previsoes_operacionais_dashboard
        where execucao_id = (select execucao_id from ultima_execucao)
        order by inicio_semana_alvo desc, horizonte asc
        """
    )
    return pd.read_sql(query, engine, parse_dates=[
        "inicio_semana_alvo", "criado_em", "gerado_em", "data_corte", "data_limite_clima"
    ])


def load_historical_predictions(engine: Engine) -> pd.DataFrame:
    """Avaliação final de 2024 da última execução, separada da fonte operacional."""
    query = text(
        """
        with ultima_execucao as (
            select execucao_id
            from public.tcc_previsoes_epidemiologicas
            group by execucao_id
            order by max(criado_em) desc, execucao_id desc
            limit 1
        )
        select inicio_semana_alvo, inicio_semana_t, horizonte,
               observado, previsto, nivel_previsto, limiar_atencao, limiar_alerta,
               execucao_id, criado_em, modelo, versao_modelo
        from public.tcc_previsoes_epidemiologicas
        where execucao_id = (select execucao_id from ultima_execucao)
        order by inicio_semana_alvo asc, horizonte asc
        """
    )
    return pd.read_sql(query, engine, parse_dates=["inicio_semana_alvo", "criado_em"])


def load_sensor_readings(engine: Engine, limit: int = 1000) -> pd.DataFrame:
    query = text(
        """
        select
            id,
            device_id,
            data_hora,
            ph_value,
            turbidity_value,
            tds_value,
            temperature_value,
            status
        from public.leituras_sensor
        order by data_hora desc, id desc
        limit :limit
        """
    )
    frame = pd.read_sql(
        query, engine, params={"limit": int(limit)}, parse_dates=["data_hora"]
    )
    return frame.sort_values("data_hora").reset_index(drop=True)
