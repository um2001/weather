import logging
from datetime import date
from time import perf_counter
from typing import Any

import httpx

from ..errors import WeatherDataInvalid, WeatherServiceUnavailable
from ..schemas import DailyForecast, ForecastData, WeatherData, WeatherQuery

logger = logging.getLogger(__name__)


class WttrProvider:
    def __init__(self, base_url: str = "https://wttr.in", timeout_seconds: float = 8.0, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self._client = client

    def get_weather(self, query: WeatherQuery) -> WeatherData:
        url = f"{self.base_url}/{query.location}"
        started = perf_counter()
        try:
            if self._client is not None:
                response = self._client.get(url, params={"format": "j1"}, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params={"format": "j1"})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "weather request failed provider=wttr location=%s error=%s duration_ms=%.1f",
                query.location,
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise WeatherServiceUnavailable("天气服务暂时不可用") from exc
        try:
            data = self._parse(payload, query)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning(
                "weather response invalid provider=wttr location=%s error=%s duration_ms=%.1f",
                query.location,
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise WeatherDataInvalid("天气服务返回的数据无法解析") from exc
        logger.info(
            "weather request succeeded provider=wttr location=%s duration_ms=%.1f",
            query.location,
            (perf_counter() - started) * 1000,
        )
        return data

    def get_forecast(self, query: WeatherQuery) -> ForecastData:
        url = f"{self.base_url}/{query.location}"
        started = perf_counter()
        try:
            if self._client is not None:
                response = self._client.get(url, params={"format": "j1"}, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params={"format": "j1"})
            response.raise_for_status()
            payload = response.json()
            forecasts = self._parse_forecast(payload, query)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "forecast request failed provider=wttr location=%s error=%s duration_ms=%.1f",
                query.location,
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise WeatherServiceUnavailable("天气预报服务暂时不可用") from exc
        logger.info(
            "forecast request succeeded provider=wttr location=%s days=%s duration_ms=%.1f",
            query.location,
            len(forecasts.days),
            (perf_counter() - started) * 1000,
        )
        return forecasts

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
            timezone=query.timezone,
        )

    @staticmethod
    def _parse_forecast(payload: dict[str, Any], query: WeatherQuery) -> ForecastData:
        days = []
        for item in payload["weather"][: query.days]:
            hourly = item.get("hourly", [{}])[0]
            desc = hourly.get("weatherDesc", [{}])[0].get("value")
            precip = hourly.get("chanceofrain") or item.get("chanceofrain")
            days.append(
                DailyForecast(
                    date=str(item["date"]),
                    weather_description=desc,
                    temperature_min_c=float(item["mintempC"]) if item.get("mintempC") is not None else None,
                    temperature_max_c=float(item["maxtempC"]) if item.get("maxtempC") is not None else None,
                    precipitation_probability_percent=int(precip) if precip is not None else None,
                )
            )
        if not days:
            raise ValueError("missing forecast days")
        return ForecastData(location=query.location, timezone=query.timezone, days=days, source="wttr.in")
