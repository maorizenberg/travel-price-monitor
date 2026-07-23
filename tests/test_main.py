from travel_monitor.main import app


def test_root():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health():
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"