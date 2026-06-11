from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok_status() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "service": "internal-exam-platform"},
        "message": "ok",
    }
