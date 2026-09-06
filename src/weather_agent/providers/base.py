from typing import Protocol

from ..schemas import WeatherData, WeatherQuery


class WeatherProvider(Protocol):
    def get_weather(self, query: WeatherQuery) -> WeatherData: ...
