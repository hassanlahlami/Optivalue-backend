from fastapi.testclient import TestClient
from config.settings import load_settings
from storage.db import connect, migrate
from api.app import create_app

def test_health_and_endpoints(tmp_path):
    s = load_settings("settings.yaml")
    db = str(tmp_path / "t.db")
    conn = connect(db); migrate(conn); conn.close()
    object.__setattr__(s, "db_path", db)  # frozen dataclass override for test
    app = create_app(s)
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/api/value-bets?date=2026-06-25").status_code == 200
    assert isinstance(c.get("/api/bets?status=open").json(), list)
    assert "sample_size" in c.get("/api/clv-report").json()
