from fastapi.testclient import TestClient

from weather_agent.api import app


def test_web_homepage_is_available():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "晴旅" in response.text
