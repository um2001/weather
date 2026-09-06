from time import monotonic
from typing import Callable, TypeVar

from .schemas import ForecastData, WeatherData, WeatherQuery

T = TypeVar("T", WeatherData, ForecastData)


class WeatherCache:
    def __init__(self, ttl_seconds: float = 120.0):
        self.ttl_seconds = ttl_seconds
        self._items: dict[tuple, tuple[float, T]] = {}

    def get_or_set(self, query: WeatherQuery, loader: Callable[[], T]) -> T:
        key = (
            query.location,
            query.date,
            query.unit,
            tuple(query.metrics),
            query.days,
            query.timezone,
        )
        now = monotonic()
        cached = self._items.get(key)
        if cached and now - cached[0] < self.ttl_seconds:
            return cached[1]
        value = loader()
        self._items[key] = (now, value)
        return value
