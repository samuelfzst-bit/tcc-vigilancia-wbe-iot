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
