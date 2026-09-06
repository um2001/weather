from weather_agent.schemas import WeatherData
from weather_agent.tools import create_get_weather_tool


class FakeProvider:
    def get_weather(self, query):
        return WeatherData(location=query.location, date=query.date, temperature_c=18, source="fake")


def test_get_weather_tool_returns_standardized_dict():
    result = create_get_weather_tool(FakeProvider()).invoke({"location": "广州"})
    assert result["location"] == "广州"
    assert result["temperature_c"] == 18
    assert "current_condition" not in result
