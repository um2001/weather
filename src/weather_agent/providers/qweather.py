import logging
from datetime import date
from time import perf_counter
from typing import Any

import httpx

from ..errors import WeatherDataInvalid, WeatherServiceUnavailable
from ..schemas import DailyForecast, ForecastData, WeatherData, WeatherQuery

logger = logging.getLogger(__name__)


class QWeatherProvider:
    """和风天气适配器，负责地点编码和天气响应标准化。"""

    def __init__(
        self,
        api_key: str,
        api_host: str = "https://devapi.qweather.com",
        geo_host: str = "https://geoapi.qweather.com",
        timeout_seconds: float = 8.0,
        client: httpx.Client | None = None,
    ):
        if not api_key.strip():
            raise ValueError("QWeather API key is required")
        self.api_key = api_key
        self.api_host = api_host.rstrip("/")
        self.geo_host = geo_host.rstrip("/")
        self.timeout = timeout_seconds
        self._client = client

    def get_weather(self, query: WeatherQuery) -> WeatherData:
        started = perf_counter()
        try:
            location_id = self._location_id(query.location)
            if query.date == "current":
                payload = self._get("/v7/weather/now", {"location": location_id})
                data = self._parse_now(payload, query)
            else:
                payload = self._get("/v7/weather/3d", {"location": location_id})
                data = self._parse_day(payload, query)
        except (WeatherDataInvalid, WeatherServiceUnavailable):
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("qweather request failed location=%s error=%s", query.location, type(exc).__name__)
            raise WeatherServiceUnavailable("天气服务暂时不可用") from exc
        logger.info("qweather request succeeded location=%s duration_ms=%.1f", query.location, (perf_counter() - started) * 1000)
        return data

    def get_forecast(self, query: WeatherQuery) -> ForecastData:
        started = perf_counter()
        try:
            location_id = self._location_id(query.location)
            payload = self._get("/v7/weather/7d", {"location": location_id})
            days = [self._parse_forecast_day(item) for item in payload["daily"][: query.days]]
            if not days:
                raise WeatherDataInvalid("missing forecast days")
        except (WeatherDataInvalid, WeatherServiceUnavailable):
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("qweather forecast failed location=%s error=%s", query.location, type(exc).__name__)
            raise WeatherServiceUnavailable("天气预报服务暂时不可用") from exc
        logger.info("qweather forecast succeeded location=%s days=%s duration_ms=%.1f", query.location, len(days), (perf_counter() - started) * 1000)
        return ForecastData(location=query.location, timezone=query.timezone, days=days, source="QWeather")

    def _location_id(self, location: str) -> str:
        payload = self._get_geo("/geo/v2/city/lookup", {"location": location, "number": 1})
        try:
            return str(payload["location"][0]["id"])
        except (KeyError, IndexError, TypeError) as exc:
            raise WeatherDataInvalid("无法识别该城市或景点") from exc

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"{self.api_host}{path}", params)

    def _get_geo(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"{self.geo_host}{path}", params)

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "key": self.api_key}
        if self._client is not None:
            response = self._client.get(url, params=params, timeout=self.timeout)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "200":
            raise WeatherServiceUnavailable("天气服务返回错误")
        return payload

    @staticmethod
    def _parse_now(payload: dict[str, Any], query: WeatherQuery) -> WeatherData:
        now = payload["now"]
        return WeatherData(
            location=query.location,
            date="current",
            temperature_c=float(now["temp"]),
            weather_description=now.get("text"),
            humidity_percent=int(now["humidity"]) if now.get("humidity") is not None else None,
            wind_speed_kmh=float(now["windSpeed"]) * 3.6 if now.get("windSpeed") is not None else None,
            wind_description=f"{now.get('windDir')} {now.get('windScale')}级" if now.get("windDir") else None,
            source="QWeather",
            timezone=query.timezone,
        )

    @classmethod
    def _parse_day(cls, payload: dict[str, Any], query: WeatherQuery) -> WeatherData:
        daily = payload["daily"]
        wanted = query.target_date or (str(date.today()) if query.date == "today" else daily[0]["fxDate"])
        item = next((value for value in daily if value.get("fxDate") == wanted), None)
        if item is None:
            raise WeatherServiceUnavailable("所查询日期暂无可靠预报")
        parsed = cls._parse_forecast_day(item)
        return WeatherData(
            location=query.location,
            date=parsed.date,
            temperature_c=parsed.temperature_max_c,
            temperature_min_c=parsed.temperature_min_c,
            temperature_max_c=parsed.temperature_max_c,
            weather_description=parsed.weather_description,
            precipitation_probability_percent=parsed.precipitation_probability_percent,
            wind_description=item.get("windDirDay") and f"{item['windDirDay']} {item.get('windScaleDay', '')}级",
            source="QWeather",
            timezone=query.timezone,
        )

    @staticmethod
    def _parse_forecast_day(item: dict[str, Any]) -> DailyForecast:
        return DailyForecast(
            date=str(item["fxDate"]),
            weather_description=item.get("textDay"),
            temperature_min_c=float(item["tempMin"]) if item.get("tempMin") is not None else None,
            temperature_max_c=float(item["tempMax"]) if item.get("tempMax") is not None else None,
            precipitation_probability_percent=int(item["precipProbability"]) if item.get("precipProbability") is not None else None,
        )
