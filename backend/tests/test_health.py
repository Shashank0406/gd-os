from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_gd_os_and_utc() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "gd-os"
    assert body["product"] == "Gamers District Operating System"
    assert body["time_utc"].endswith("+00:00")
