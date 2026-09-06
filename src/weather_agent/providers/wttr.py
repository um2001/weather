import logging
from datetime import date
from typing import Any

import httpx

from ..errors import WeatherDataInvalid, WeatherServiceUnavailable
from ..schemas import WeatherData, WeatherQuery

logger = logging.getLogger(__name__)


class WttrProvider:
    def __init__(self, base_url: str = "https://wttr.in", timeout_seconds: float = 8.0, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self._client = client

    def get_weather(self, query: WeatherQuery) -> WeatherData:
        url = f"{self.base_url}/{query.location}"
        try:
            if self._client is not None:
                response = self._client.get(url, params={"format": "j1"}, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params={"format": "j1"})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("weather request failed provider=wttr error=%s", type(exc).__name__)
            raise WeatherServiceUnavailable("天气服务暂时不可用") from exc
        try:
            return self._parse(payload, query)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("weather response invalid provider=wttr error=%s", type(exc).__name__)
            raise WeatherDataInvalid("天气服务返回的数据无法解析") from exc

    @staticmethod
    def _parse(payload: dict[str, Any], query: WeatherQuery) -> WeatherData:
        current = payload["current_condition"][0]
        day = payload.get("weather", [{}])[0]
        hourly = day.get("hourly", [{}])[0]
        description = current.get("weatherDesc", [{}])[0].get("value")
        temperature = current.get("temp_C")
        if temperature is None:
            raise ValueError("missing temperature")
        precip = hourly.get("chanceofrain") or day.get("chanceofrain")
        return WeatherData(
            location=query.location,
            date=str(date.today()) if query.date == "today" else "current",
            temperature_c=float(temperature),
            weather_description=description,
            humidity_percent=int(current["humidity"]) if current.get("humidity") is not None else None,
            wind_speed_kmh=float(current["windspeedKmph"]) if current.get("windspeedKmph") is not None else None,
            precipitation_probability_percent=int(precip) if precip is not None else None,
            source="wttr.in",
        )
