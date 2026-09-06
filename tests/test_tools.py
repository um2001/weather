from weather_agent.providers.wttr import WttrProvider
from weather_agent.tools import create_get_weather_tool


class FakeProvider:
    def get_weather(self, query):
        return WttrProvider._parse({"current_condition": [{"temp_C": "18"}], "weather": [{}]}, query)


def test_get_weather_tool_returns_standardized_dict():
    result = create_get_weather_tool(FakeProvider()).invoke({"location": "广州"})
    assert result["location"] == "广州"
    assert result["temperature_c"] == 18
    assert "current_condition" not in result
