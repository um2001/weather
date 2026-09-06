from fastapi.testclient import TestClient

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
    assert response.json() == {"reply": "上海今天24°C。", "status": "success"}


def test_chat_api_rejects_blank_message():
    response = TestClient(app).post("/api/chat", json={"message": "   "})
    assert response.status_code == 422
