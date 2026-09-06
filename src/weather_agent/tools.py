from langchain_core.tools import StructuredTool

from .schemas import WeatherData, WeatherQuery
from .providers.base import WeatherProvider


def get_weather(query: WeatherQuery, provider: WeatherProvider) -> WeatherData:
    """Fetch and normalize weather data through the configured provider."""
    return provider.get_weather(query)


def create_get_weather_tool(provider: WeatherProvider) -> StructuredTool:
    def _run(location: str, date: str = "today", unit: str = "celsius", metrics: list[str] | None = None) -> dict:
        query = WeatherQuery(location=location, date=date, unit=unit, metrics=metrics or [])
        return get_weather(query, provider).model_dump()

    return StructuredTool.from_function(
        _run,
        name="get_weather",
        description="查询指定城市当前或今天的天气，返回标准化天气数据。",
    )
