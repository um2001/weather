from weather_agent.agent import WeatherAgent
from weather_agent.errors import WeatherServiceUnavailable
from weather_agent.schemas import WeatherData


class FakeProvider:
    def __init__(self, error=False):
        self.error = error
        self.queries = []

    def get_weather(self, query):
        self.queries.append(query)
        if self.error:
            raise WeatherServiceUnavailable()
        return WeatherData(location=query.location, date=query.date, temperature_c=22, weather_description="晴", precipitation_probability_percent=10, source="fake")


def test_agent_calls_weather_tool_and_answers_in_chinese():
    provider = FakeProvider()
    answer = WeatherAgent(provider).answer("上海今天会下雨吗？")
    assert provider.queries[0].location == "上海"
    assert "上海" in answer and "22°C" in answer and "降雨概率10%" in answer


def test_agent_asks_for_location_when_missing():
    provider = FakeProvider()
    assert "城市或地区" in WeatherAgent(provider).answer("今天会下雨吗？")
    assert provider.queries == []


def test_agent_does_not_fabricate_when_service_fails():
    answer = WeatherAgent(FakeProvider(error=True)).answer("北京天气怎么样")
    assert "暂时无法使用" in answer
    assert "°C" not in answer
