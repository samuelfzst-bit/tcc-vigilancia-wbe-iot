"""Execução e diagnóstico de leituras, sem dependência da interface Streamlit."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import logging
import os
from pathlib import Path
import time
import tomllib
from typing import Callable

import pandas as pd

BRASILIA = timezone(timedelta(hours=-3))
REFRESH_SECONDS = 30
LOGGER = logging.getLogger("wbe.dashboard.queries")


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class QueryIssue:
    code: str
    message: str


@dataclass
class QueryResult:
    frame: pd.DataFrame
    attempted_at: datetime
    fetched_at: datetime | None
    elapsed_ms: int
    issue: QueryIssue | None = None


def load_local_secrets(root: Path):
    if os.getenv("TCC_DB_URL"):
        return {}
    for path in (root / ".streamlit" / "secrets.toml", root / "frontend" / ".streamlit" / "secrets.toml"):
        try:
            with path.open("rb") as source:
                secrets = tomllib.load(source)
        except FileNotFoundError:
            continue
        except (OSError, tomllib.TOMLDecodeError):
            raise ConfigurationError("Configuração local indisponível ou inválida.") from None
        if secrets.get("TCC_DB_URL"):
            return secrets
    return {}


def classify_error(exc):
    code = getattr(getattr(exc, "orig", None), "sqlstate", None)
    if isinstance(exc, ConfigurationError):
        return QueryIssue("configuration", "Configuração de acesso ausente ou inválida. Confira TCC_DB_URL no arquivo local de segredos.")
    if code in ("28P01", "28000"):
        return QueryIssue("authentication", "O banco recusou as credenciais configuradas.")
    if code == "42501":
        return QueryIssue("permission", "O usuário configurado não tem permissão de leitura nesta fonte.")
    if code in ("42P01", "42703"):
        return QueryIssue("schema", "A fonte não corresponde às tabelas ou colunas esperadas pelo dashboard.")
    if code in ("57014", "53300") or type(exc).__name__ == "TimeoutError":
        return QueryIssue("timeout", "A consulta excedeu o prazo ou o banco está ocupado. A próxima atualização tentará novamente.")
    if type(exc).__name__ in ("OperationalError", "InterfaceError"):
        return QueryIssue("connection", "A fonte está indisponível. Confira a conexão e o endereço configurado.")
    return QueryIssue("query", "Não foi possível atualizar esta fonte. Confira o diagnóstico local.")


def execute_read(loader: Callable[[], pd.DataFrame], source: str, *, clock=None, timer=None):
    if source not in ("sensors", "forecasts", "historical_forecasts"):
        raise ValueError("Fonte desconhecida.")
    clock = clock or (lambda: datetime.now(timezone.utc))
    timer = timer or time.monotonic
    attempted = clock()
    started = timer()
    try:
        frame = loader()
        if not isinstance(frame, pd.DataFrame):
            issue = QueryIssue("contract", "A consulta retornou um formato inválido.")
            frame = pd.DataFrame()
        else:
            issue = None
            frame = frame.copy()
    except Exception as exc:
        issue = classify_error(exc)
        frame = pd.DataFrame()
    elapsed = max(0, round((timer() - started) * 1000))
    result = QueryResult(frame, attempted, clock() if issue is None else None, elapsed, issue)
    # Não registrar DSN, parâmetros, dados de leituras ou mensagens brutas de exceções.
    event = {"event": "dashboard_query", "source": source, "outcome": issue.code if issue else "ok", "rows": len(frame), "elapsed_ms": elapsed}
    LOGGER.log(logging.WARNING if issue else logging.INFO, json.dumps(event))
    return result


def refresh_due(now, last_poll, enabled=True):
    return enabled and (last_poll is None or now - last_poll >= REFRESH_SECONDS)


def latest_success_at(results):
    return max((r.fetched_at for r in results if r.issue is None and r.fetched_at is not None), default=None)


def update_status(results, *, invalid_contract=False):
    failures = [r for r in results if r.issue]
    if invalid_contract:
        return "Dados inconsistentes", "attention", "Confira o diagnóstico na aba Qualidade dos dados."
    if failures:
        label = "Atualização parcial" if len(failures) < len(results) else "Falha na atualização"
        return label, "attention", " • ".join(r.issue.message for r in failures)
    latest = latest_success_at(results)
    if latest is None:
        return "Aguardando dados", "unavailable", "Ainda não há consulta concluída."
    completed = latest.astimezone(BRASILIA)
    return f"Atualizado às {completed:%H:%M:%S}", "normal", (
        f"Ciclo de consultas concluído em {completed:%d/%m/%Y %H:%M:%S} (Brasília). "
        "Inclui sensores, previsões operacionais e avaliação final de 2024."
    )
