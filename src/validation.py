"""Contrato mínimo do dataset temporal de modelagem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Contract:
    scenario: str = "principal_sem_importados_conhecidos"
    availability_source: str = "DT_ENCERRA"
    train_max_year: int = 2022
    validation_year: int = 2023
    test_year: int = 2024


REQUIRED_COLUMNS = {
    "horizonte",
    "inicio_semana_t",
    "data_corte",
    "inicio_semana_alvo",
    "ano_alvo",
    "target_casos",
    "split",
    "cenario_geografico",
    "fonte_disponibilidade",
}

FORBIDDEN_FEATURES = {"casos_t_mais_1", "casos_t_mais_2"}


def _require_columns(columns: Iterable[str]) -> None:
    columns = set(columns)
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing)}")
    forbidden = FORBIDDEN_FEATURES & columns
    if forbidden:
        raise ValueError(f"Possível leakage: {sorted(forbidden)}")


def validate_dataset(df: pd.DataFrame, contract: Contract = Contract()) -> None:
    """Falha cedo se o snapshot violar o desenho temporal aprovado."""

    _require_columns(df.columns)
    if df.empty:
        raise ValueError("Dataset vazio")

    work = df.copy()
    for column in ("inicio_semana_t", "data_corte", "inicio_semana_alvo"):
        work[column] = pd.to_datetime(work[column], errors="raise")

    if work[["horizonte", "inicio_semana_t"]].duplicated().any():
        raise ValueError("Chave (horizonte, inicio_semana_t) duplicada")
    if work["target_casos"].isna().any() or (work["target_casos"] < 0).any():
        raise ValueError("Alvo nulo ou negativo")
    if not (work["data_corte"] == work["inicio_semana_t"] + pd.Timedelta(days=6)).all():
        raise ValueError("data_corte deve ser o domingo da semana t")
    if not (work["inicio_semana_alvo"] > work["data_corte"]).all():
        raise ValueError("Alvo não está estritamente no futuro")

    expected_days = work["horizonte"].map({1: 7, 2: 14})
    if expected_days.isna().any():
        raise ValueError("Horizonte deve ser 1 ou 2")
    delta = (work["inicio_semana_alvo"] - work["inicio_semana_t"]).dt.days
    if not delta.eq(expected_days).all():
        raise ValueError("Deslocamento temporal incompatível com o horizonte")

    if set(work["cenario_geografico"].dropna().unique()) != {contract.scenario}:
        raise ValueError("Cenário diferente do cenário principal aprovado")
    if set(work["fonte_disponibilidade"].dropna().unique()) != {contract.availability_source}:
        raise ValueError("Fonte de disponibilidade deve ser DT_ENCERRA")

    years = pd.to_numeric(work["ano_alvo"], errors="raise")
    if (years < 2010).any() or (years > contract.test_year).any():
        raise ValueError("Período fora do escopo aprovado de 2010 a 2024")
    expected_split = pd.Series("treino", index=work.index)
    expected_split.loc[years == contract.validation_year] = "validacao"
    expected_split.loc[years == contract.test_year] = "teste"
    expected_split.loc[years > contract.test_year] = "fora_do_escopo"
    if not work["split"].astype(str).eq(expected_split).all():
        raise ValueError("Split temporal divergente: treino<=2022, validação=2023, teste=2024")
