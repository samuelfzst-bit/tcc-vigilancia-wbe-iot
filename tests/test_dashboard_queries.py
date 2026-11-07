from datetime import datetime, timedelta, timezone
import logging

import pandas as pd

from frontend.query_service import (
    ConfigurationError, QueryIssue, QueryResult, execute_read, load_local_secrets,
    refresh_due, update_status,
)


def test_success_timestamp_is_query_completion_not_render_time():
    started = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
    finished = started + timedelta(seconds=1)
    clocks = iter([started, finished])
    timers = iter([10., 11.])
    result = execute_read(lambda: pd.DataFrame({"value": [1]}), "sensors", clock=lambda: next(clocks), timer=lambda: next(timers))
    assert result.attempted_at == started and result.fetched_at == finished
    assert result.elapsed_ms == 1000 and result.issue is None
    assert update_status([result, result])[0] == "Atualizado às 07:00:01"


def test_failure_is_not_labeled_fresh_and_does_not_leak_exception(caplog):
    marker = "dummy-secret-that-must-not-be-logged"
    def failing_loader():
        raise RuntimeError("postgresql://fixture:" + marker + "@dummy.invalid/db")
    with caplog.at_level(logging.INFO, logger="wbe.dashboard.queries"):
        failed = execute_read(failing_loader, "sensors")
    assert failed.fetched_at is None and failed.issue is not None
    assert marker not in caplog.text and marker not in failed.issue.message
    assert update_status([failed, failed])[0] == "Falha na atualização"


def test_wrong_contract_is_distinct_from_empty_success():
    bad = execute_read(lambda: [], "forecasts")
    empty = execute_read(lambda: pd.DataFrame(), "sensors")
    assert bad.issue.code == "contract" and bad.fetched_at is None
    assert empty.issue is None and empty.fetched_at is not None
    assert update_status([empty, bad])[0] == "Atualização parcial"


def test_one_source_failure_keeps_the_other_result_independent():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    good = QueryResult(pd.DataFrame({"value": [3]}), now, now, 2)
    failed = QueryResult(pd.DataFrame(), now, None, 4, QueryIssue("connection", "Fonte indisponível"))
    assert update_status([good, failed])[0] == "Atualização parcial"
    assert good.frame.iloc[0]["value"] == 3


def test_automatic_deadline_is_independent_of_widget_renders():
    last_poll = 100.
    for now in (101., 110., 120., 129.9):
        assert not refresh_due(now, last_poll)
    assert refresh_due(130., last_poll)
    assert not refresh_due(131., last_poll, enabled=False)
    assert not refresh_due(159., 130.)
    assert refresh_due(160., 130.)


def test_local_config_validation_never_uses_or_exposes_real_secrets(tmp_path, monkeypatch):
    monkeypatch.delenv("TCC_DB_URL", raising=False)
    folder = tmp_path / ".streamlit"
    folder.mkdir()
    (folder / "secrets.toml").write_text('TCC_DB_URL = "unterminated-dummy-secret', encoding="utf-8")
    def load():
        load_local_secrets(tmp_path)
        return pd.DataFrame()
    result = execute_read(load, "sensors")
    assert result.issue.code == "configuration"
    assert "unterminated-dummy-secret" not in result.issue.message
    assert result.fetched_at is None


def test_environment_configuration_does_not_read_local_files(tmp_path, monkeypatch):
    monkeypatch.setenv("TCC_DB_URL", "postgresql://fixture:dummy@dummy.invalid/db")
    assert load_local_secrets(tmp_path) == {}


def test_configuration_failure_is_a_distinct_safe_category():
    def loader():
        raise ConfigurationError("dummy-private-context")
    result = execute_read(loader, "forecasts")
    assert result.issue.code == "configuration"
    assert "dummy-private-context" not in result.issue.message


def test_update_status_local_time_handles_previous_day_without_changing_source():
    fetched = datetime(2026, 11, 1, 1, 39, tzinfo=timezone.utc)
    result = QueryResult(pd.DataFrame(), fetched, fetched, 1)
    earlier = QueryResult(pd.DataFrame(), fetched, fetched.replace(minute=38), 1)
    label, _, detail = update_status([earlier, result])
    assert label == "Atualizado às 22:39:00"
    assert "31/10/2026 22:39:00" in detail
    assert result.fetched_at == fetched
