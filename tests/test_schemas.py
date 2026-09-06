import pytest
from pydantic import ValidationError

from weather_agent.schemas import WeatherData, WeatherQuery


def test_weather_query_defaults_and_normalizes_location():
    query = WeatherQuery(location="  北京 ")
    assert query.location == "北京"
    assert query.date == "today"
    assert query.unit == "celsius"


def test_weather_query_rejects_blank_location():
    with pytest.raises(ValidationError):
        WeatherQuery(location=" ")


def test_weather_data_allows_optional_metrics():
    data = WeatherData(location="北京", date="today", temperature_c=20, source="test")
    assert data.humidity_percent is None


def test_chat_request_limits_message_and_history_size():
    from weather_agent.schemas import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 2001)
    with pytest.raises(ValidationError):
        ChatRequest(message="上海", history=[{"role": "user", "content": "x"}] * 21)
