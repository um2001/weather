from fastapi.testclient import TestClient

from weather_agent.api import app


def test_web_homepage_is_available():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "晴旅" in response.text


def test_weather_card_distinguishes_probability_from_precipitation_amount():
    response = TestClient(app).get("/web/app.js")

    assert response.status_code == 200
    assert "降雨概率 ${day.precipitation_probability_percent}%" in response.text
    assert "预计降水 ${day.precipitation_mm} mm" in response.text
    assert "降水数据暂缺" in response.text


def test_web_chat_handles_stale_conversation_and_reenables_submit():
    response = TestClient(app).get("/web/app.js")

    assert "response.status === 404 && conversationId" in response.text
    assert "submit.disabled = true" in response.text
    assert "submit.disabled = false" in response.text
