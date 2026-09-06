import logging
import re
from collections.abc import Callable

from .errors import WeatherServiceError
from .providers.base import WeatherProvider
from .schemas import WeatherData, WeatherQuery
from .tools import get_weather

logger = logging.getLogger(__name__)


class WeatherAgent:
    def __init__(self, provider: WeatherProvider, query_extractor: Callable[[str], WeatherQuery | None] | None = None):
        self.provider = provider
        self.query_extractor = query_extractor

    def answer(self, user_input: str) -> str:
        if not self._is_weather_request(user_input):
            return "我目前只支持查询城市的当前或今日天气。"
        if any(word in user_input for word in ("长期气候", "未来7天", "未来七天", "气候分析")):
            return "目前仅支持查询当前或今天的天气，暂不支持长期预报或气候分析。"
        query = self.query_extractor(user_input) if self.query_extractor else self._extract_query(user_input)
        if query is None:
            return "请告诉我想查询的城市或地区。"
        try:
            data = get_weather(query, self.provider)
        except WeatherServiceError:
            logger.info("weather query failed location=%s", query.location)
            return "抱歉，天气服务暂时无法使用，请稍后再试。"
        return self._format_answer(data)

    @staticmethod
    def _is_weather_request(text: str) -> bool:
        return any(word in text for word in ("天气", "下雨", "温度", "湿度", "风速", "降雨"))

    @staticmethod
    def _extract_query(text: str) -> WeatherQuery | None:
        cleaned = re.sub(r"[，。！？?！,.]", "", text).strip()
        normalized = re.sub(r"^(请问|帮我查一下|帮我查|查询|查一下|查)\s*", "", cleaned).strip()
        match = re.search(r"(?:今天|今日|现在|当前|天气|会下雨|下雨)", normalized)
        location = normalized[: match.start()] if match else normalized
        location = location.strip()
        location = re.sub(r"(的)$", "", location).strip()
        if not location or location in {"今天", "今日", "现在", "当前"}:
            return None
        current = any(word in cleaned for word in ("现在", "当前"))
        return WeatherQuery(location=location, date="current" if current else "today")

    @staticmethod
    def _format_answer(data: WeatherData) -> str:
        parts = [f"{data.location}（{data.date}）"]
        if data.weather_description:
            parts.append(data.weather_description)
        if data.temperature_c is not None:
            parts.append(f"{data.temperature_c:g}°C")
        if data.humidity_percent is not None:
            parts.append(f"湿度{data.humidity_percent}%")
        if data.wind_speed_kmh is not None:
            parts.append(f"风速{data.wind_speed_kmh:g} km/h")
        if data.precipitation_probability_percent is not None:
            parts.append(f"降雨概率{data.precipitation_probability_percent}%")
        return "，".join(parts) + "。"
