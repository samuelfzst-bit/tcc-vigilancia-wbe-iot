from frontend.data_access import database_url


def test_database_url_accepts_explicit_psycopg(monkeypatch):
    monkeypatch.setenv(
        "TCC_DB_URL",
        "postgresql+psycopg://usuario:senha@host:6543/postgres",
    )

    assert database_url().startswith("postgresql+psycopg://")


def test_database_url_normalizes_supabase_postgresql_uri(monkeypatch):
    monkeypatch.setenv(
        "TCC_DB_URL",
        "postgresql://usuario:senha@host:6543/postgres",
    )

    assert database_url().startswith("postgresql+psycopg://")


def test_database_url_rejects_non_postgresql_uri(monkeypatch):
    monkeypatch.setenv("TCC_DB_URL", "https://example.com")

    try:
        database_url()
    except RuntimeError as exc:
        assert "TCC_DB_URL" in str(exc)
    else:
        raise AssertionError("URI não PostgreSQL deveria ser rejeitada")


def test_predictions_use_operational_view_and_generation_date_only(monkeypatch):
    import pandas as pd
    from frontend import data_access
    captured = {}
    expected = pd.DataFrame({"observado": [None], "previsto": [3.28]})
    engine = object()
    def read(query, selected_engine, parse_dates):
        captured.update(sql=str(query), engine=selected_engine, dates=parse_dates)
        return expected
    monkeypatch.setattr(data_access.pd, "read_sql", read)
    actual = data_access.load_predictions(engine)
    assert "public.tcc_previsoes_operacionais_dashboard" in captured["sql"]
    assert "max(gerado_em) desc" in captured["sql"]
    assert "observado_provisorio as observado" in captured["sql"]
    assert "gerado_em as criado_em" in captured["sql"]
    assert "tcc_previsoes_epidemiologicas" not in captured["sql"]
    assert captured["engine"] is engine
    assert "gerado_em" in captured["dates"]
    pd.testing.assert_frame_equal(actual, expected)


def test_historical_predictions_load_complete_latest_evaluation(monkeypatch):
    import pandas as pd
    from frontend import data_access
    captured = {}
    def read(query, engine, parse_dates):
        captured.update(sql=str(query), dates=parse_dates)
        return pd.DataFrame()
    monkeypatch.setattr(data_access.pd, "read_sql", read)
    data_access.load_historical_predictions(object())
    assert "public.tcc_previsoes_epidemiologicas" in captured["sql"]
    assert "max(criado_em) desc" in captured["sql"]
    assert "operacionais" not in captured["sql"]
    assert "where execucao_id" in captured["sql"]
    assert "inicio_semana_alvo asc, horizonte asc" in captured["sql"]
    assert captured["sql"].lower().count("limit") == 1  # somente execução, nunca semanas
