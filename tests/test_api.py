from fastapi.testclient import TestClient
from pathlib import Path
import importlib

from weather_agent.agent import WeatherAgent
from weather_agent.api import app
from weather_agent.schemas import WeatherData, WeatherIntent


class FakeProvider:
    def get_weather(self, query):
        return WeatherData(location=query.location, date=query.date, temperature_c=24, source="fake")


class FakeLanguageModel:
    def extract_intent(self, message, history):
        location = message if message == "上海" else None
        return WeatherIntent(kind="weather", location=location)

    def generate_answer(self, message, history, data):
        return f"{data.location}今天{data.temperature_c:g}°C。"


def test_chat_api_supports_history_follow_up():
    app.state.weather_agent = WeatherAgent(FakeProvider(), language_model=FakeLanguageModel())
    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "上海",
            "history": [
                {"role": "user", "content": "今天会下雨吗？"},
                {"role": "assistant", "content": "请告诉我想查询的城市或地区。"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "上海今天24°C。"
    assert response.json()["status"] == "success"


def test_chat_api_rejects_blank_message():
    response = TestClient(app).post("/api/chat", json={"message": "   "})
    assert response.status_code == 422


def test_health_endpoint_does_not_require_llm_configuration():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_api_logs_request(caplog):
    caplog.set_level("INFO", logger="weather_agent.api")
    app.state.weather_agent = WeatherAgent(FakeProvider(), language_model=FakeLanguageModel())

    response = TestClient(app).post("/api/chat", json={"message": "上海"})

    assert response.status_code == 200
    assert any("api request" in record.message and "duration_ms=" in record.message for record in caplog.records)


def test_conversation_delete_endpoint_removes_conversation():
    created = TestClient(app).post("/api/conversations")
    conversation_id = created.json()["id"]

    response = TestClient(app).delete(f"/api/conversations/{conversation_id}")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert TestClient(app).get(f"/api/conversations/{conversation_id}").status_code == 404


def test_api_store_uses_project_env_database_path(monkeypatch, tmp_path):
    env_path = tmp_path / "configured.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEATHER_DB_PATH", str(env_path))

    import weather_agent.api as api_module

    reloaded = importlib.reload(api_module)
    try:
        assert Path(reloaded.store.path) == env_path
    finally:
        # Keep the module usable for the remaining tests in this process.
        monkeypatch.delenv("WEATHER_DB_PATH", raising=False)
        importlib.reload(api_module)
