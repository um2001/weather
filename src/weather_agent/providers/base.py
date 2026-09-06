from typing import Protocol

from ..schemas import ForecastData, WeatherData, WeatherQuery


class WeatherProvider(Protocol):
    def get_weather(self, query: WeatherQuery) -> WeatherData: ...

    def get_forecast(self, query: WeatherQuery) -> ForecastData: ...

    def resolve_place(self, name: str, city: str | None = None): ...
