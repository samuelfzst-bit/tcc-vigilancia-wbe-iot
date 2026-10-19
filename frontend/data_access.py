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
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


def load_predictions(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        select
            inicio_semana_alvo,
            horizonte,
            observado,
            previsto,
            nivel_previsto,
            limiar_atencao,
            limiar_alerta,
            alerta_observado,
            alerta_previsto,
            erro,
            erro_absoluto,
            modelo,
            versao_modelo,
            execucao_id
        from public.tcc_previsoes_epidemiologicas
        order by inicio_semana_alvo, horizonte
        """
    )
    return pd.read_sql(query, engine, parse_dates=["inicio_semana_alvo"])


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
        order by data_hora desc
        limit :limit
        """
    )
    frame = pd.read_sql(
        query, engine, params={"limit": int(limit)}, parse_dates=["data_hora"]
    )
    return frame.sort_values("data_hora").reset_index(drop=True)
