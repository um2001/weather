import logging
import re
from collections.abc import Callable

from .cache import WeatherCache
from .errors import LanguageModelError, WeatherServiceError
from .llm import WeatherLanguageModel
from .location import resolve_location
from .providers.base import WeatherProvider
from .schemas import ChatMessage, ChatResponse, ForecastData, WeatherData, WeatherQuery
from .tools import get_weather

logger = logging.getLogger(__name__)


class WeatherAgent:
    def __init__(
        self,
        provider: WeatherProvider,
        query_extractor: Callable[[str], WeatherQuery | None] | None = None,
        language_model: WeatherLanguageModel | None = None,
        cache: WeatherCache | None = None,
    ):
        self.provider = provider
        self.query_extractor = query_extractor
        self.language_model = language_model
        self.cache = cache or WeatherCache()

    def answer(self, user_input: str, history: list[ChatMessage] | None = None) -> str:
        return self.respond(user_input, history).reply

    def respond(self, user_input: str, history: list[ChatMessage] | None = None) -> ChatResponse:
        history = history or []
        if self.language_model:
            return self._respond_with_model(user_input, history)
        if not self._is_weather_request(user_input):
            return ChatResponse(reply="我目前只支持查询城市的当前或今日天气。", status="unsupported")
        if any(
            word in user_input
            for word in ("明天", "后天", "下周", "未来3天", "未来三天", "未来7天", "未来七天", "多日", "长期气候", "气候分析")
        ):
            return ChatResponse(reply="目前仅支持查询当前或今天的天气，暂不支持长期预报或气候分析。", status="unsupported")
        query = self.query_extractor(user_input) if self.query_extractor else self._extract_query(user_input)
        if query is None:
            return ChatResponse(reply="请告诉我想查询的城市或地区。", status="clarification")
        return self._fetch_and_answer(query, user_input, history)

    def _respond_with_model(self, user_input: str, history: list[ChatMessage]) -> ChatResponse:
        try:
            intent = self.language_model.extract_intent(user_input, history)
        except LanguageModelError:
            return ChatResponse(reply="抱歉，大模型服务暂时无法使用，请稍后再试。", status="error")
        if intent.kind == "other":
            return ChatResponse(reply="我目前只支持查询城市的当前或今日天气。", status="unsupported")
        if intent.kind == "unsupported":
            return ChatResponse(reply="目前仅支持查询当前或今天的天气，暂不支持该天气需求。", status="unsupported")
        if not intent.location or not intent.location.strip():
            return ChatResponse(reply="请告诉我想查询的城市或地区。", status="clarification")
        resolved = resolve_location(intent.location)
        query = WeatherQuery(
            location=resolved.name,
            date=intent.date,
            metrics=intent.metrics,
            days=intent.days,
            timezone=resolved.timezone,
        )
        return self._fetch_and_answer(query, user_input, history)

    def _fetch_and_answer(
        self, query: WeatherQuery, user_input: str, history: list[ChatMessage]
    ) -> ChatResponse:
        try:
            if query.date == "forecast":
                forecast = self.cache.get_or_set(query, lambda: self.provider.get_forecast(query))
                return ChatResponse(reply=self._format_forecast(forecast), status="success")
            data = self.cache.get_or_set(query, lambda: get_weather(query, self.provider))
        except WeatherServiceError:
            logger.info("weather query failed location=%s", query.location)
            return ChatResponse(reply="抱歉，天气服务暂时无法使用，请稍后再试。", status="error")
        if self.language_model:
            try:
                reply = self.language_model.generate_answer(user_input, history, data)
            except LanguageModelError:
                reply = self._format_answer(data)
        else:
            reply = self._format_answer(data)
        return ChatResponse(reply=reply, status="success")

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
        forecast = any(word in cleaned for word in ("明天", "后天", "下周", "未来3天", "未来三天", "未来7天", "未来七天", "多日"))
        resolved = resolve_location(location)
        return WeatherQuery(location=resolved.name, date="forecast" if forecast else ("current" if current else "today"), timezone=resolved.timezone)

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

    @staticmethod
    def _format_forecast(data: ForecastData) -> str:
        parts = [f"{data.location}未来{len(data.days)}天天气预报"]
        for day in data.days:
            values = [day.date]
            if day.weather_description:
                values.append(day.weather_description)
            if day.temperature_min_c is not None and day.temperature_max_c is not None:
                values.append(f"{day.temperature_min_c:g}～{day.temperature_max_c:g}°C")
            if day.precipitation_probability_percent is not None:
                values.append(f"降雨概率{day.precipitation_probability_percent}%")
            parts.append(f"{values[0]}：{'，'.join(values[1:])}")
        return "；".join(parts) + "。"
