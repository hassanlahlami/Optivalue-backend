from fastapi.testclient import TestClient
from config.settings import load_settings
from storage.db import connect, migrate
from api.app import create_app


def _client(tmp_path):
    s = load_settings("settings.yaml")
    db = str(tmp_path / "t.db")
    conn = connect(db)
    migrate(conn)
    conn.close()
    object.__setattr__(s, "db_path", db)
    return TestClient(create_app(s))


def test_bankroll_endpoint(tmp_path):
    r = _client(tmp_path).get("/api/bankroll").json()
    assert "curve" in r
    assert r["starting"] == r["current"]      # nothing settled yet
    assert r["risk_of_ruin"] == 0.0           # no open bets


def test_clv_series_endpoint(tmp_path):
    assert _client(tmp_path).get("/api/clv-series").json() == []
