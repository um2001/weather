import logging
import re
from collections.abc import Callable
from datetime import date, timedelta

from .cache import WeatherCache
from .errors import LanguageModelError, LanguageModelResponseError, WeatherServiceError
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
            return ChatResponse(reply="我目前只支持查询城市的当前、今日或未来 3～7 天天气。", status="unsupported")
        if any(
            word in user_input
            for word in ("长期气候", "气候分析")
        ):
            return ChatResponse(reply="目前支持当前、今日或未来 3～7 天预报，暂不支持长期气候分析。", status="unsupported")
        query = self.query_extractor(user_input) if self.query_extractor else self._extract_query(user_input)
        if query is None:
            return ChatResponse(reply="请告诉我想查询的城市或地区。", status="clarification")
        return self._fetch_and_answer(query, user_input, history)

    def _respond_with_model(self, user_input: str, history: list[ChatMessage]) -> ChatResponse:
        try:
            intent = self.language_model.extract_intent(user_input, history)
        except LanguageModelResponseError:
            return ChatResponse(reply="大模型返回的查询格式无法识别，请换一种说法再试。", status="error")
        except LanguageModelError:
            return ChatResponse(reply="大模型服务暂时无法使用，请稍后再试。", status="error")
        if intent.kind == "other":
            try:
                reply = self.language_model.chat(user_input, history)
            except LanguageModelError:
                return ChatResponse(reply="大模型服务暂时无法使用，请稍后再试。", status="error")
            return ChatResponse(reply=reply, status="success")
        if intent.kind == "unsupported":
            return ChatResponse(reply="目前仅支持查询当前或今天的天气，暂不支持该天气需求。", status="unsupported")
        attraction = intent.attraction or (intent.attractions[0] if intent.attractions else None)
        place_name = attraction or intent.location
        if not place_name or not place_name.strip():
            return ChatResponse(reply="请告诉我想查询的城市或地区。", status="clarification")
        resolved = resolve_location(intent.location or place_name)
        latitude = longitude = None
        display_name = resolved.name
        resolver = getattr(self.provider, "resolve_place", None)
        # POI geocoding is only needed for explicit attraction/travel queries.
        # Ordinary city weather requests should go straight through the city
        # lookup performed by the weather provider; treating every location as
        # a POI makes valid cities such as 哈尔滨 fail with a POI 404.
        if attraction and resolver is not None:
            try:
                place = resolver(place_name, city=intent.location if attraction else None)
                display_name = place.name
                latitude, longitude = place.latitude, place.longitude
                timezone = place.timezone or resolved.timezone
            except WeatherServiceError:
                return ChatResponse(reply="无法确认这个景点的位置，请补充所在城市。", status="clarification")
        else:
            timezone = resolved.timezone
        target_date = intent.target_date or self._relative_date(user_input)
        recent_forecast = self._is_recent_forecast_request(user_input)
        generic_forecast = self._is_generic_weather_request(user_input) and not target_date
        query_date = "forecast" if recent_forecast or generic_forecast else intent.date
        days = 4 if recent_forecast or generic_forecast else (max(3, min(7, intent.days)) if query_date == "forecast" else 3)
        target_date = None if recent_forecast or generic_forecast else target_date
        query = WeatherQuery(
            location=display_name,
            date="today" if target_date else query_date,
            metrics=intent.metrics,
            days=days,
            timezone=timezone,
            target_date=target_date,
            latitude=latitude,
            longitude=longitude,
        )
        return self._fetch_and_answer(query, user_input, history, travel=intent.kind == "travel")

    def _fetch_and_answer(
        self, query: WeatherQuery, user_input: str, history: list[ChatMessage], travel: bool = False
    ) -> ChatResponse:
        try:
            if query.target_date:
                data = self.cache.get_or_set(query, lambda: self.provider.get_weather(query))
                if self.language_model:
                    try:
                        reply = self.language_model.generate_answer(user_input, history, data)
                    except LanguageModelError:
                        reply = self._format_travel_answer(data) if travel else self._format_answer(data)
                else:
                    reply = self._format_travel_answer(data) if travel else self._format_answer(data)
                return ChatResponse(reply=reply, status="success", weather=data)
            if query.date == "forecast":
                forecast = self.cache.get_or_set(query, lambda: self.provider.get_forecast(query))
                if self.language_model:
                    try:
                        reply = self.language_model.generate_answer(user_input, history, forecast)
                    except LanguageModelError:
                        reply = self._format_forecast(forecast)
                else:
                    reply = self._format_forecast(forecast)
                return ChatResponse(reply=reply, status="success", weather=forecast)
            data = self.cache.get_or_set(query, lambda: get_weather(query, self.provider))
        except WeatherServiceError as exc:
            logger.info("weather query failed location=%s", query.location)
            if "Host 未获当前 Key 授权" in str(exc):
                return ChatResponse(reply=str(exc), status="error")
            return ChatResponse(reply="抱歉，天气服务暂时无法使用，请稍后再试。", status="error")
        if self.language_model:
            try:
                reply = self.language_model.generate_answer(user_input, history, data)
            except LanguageModelError:
                reply = self._format_answer(data)
        else:
            reply = self._format_answer(data)
        return ChatResponse(reply=reply, status="success", weather=data)

    @staticmethod
    def _relative_date(text: str) -> str | None:
        today = date.today()
        if "后天" in text:
            return str(today + timedelta(days=2))
        if "明天" in text:
            return str(today + timedelta(days=1))
        return None

    @staticmethod
    def _is_recent_forecast_request(text: str) -> bool:
        return (
            any(term in text for term in ("最近", "近期", "近几天", "这几天", "这几日", "未来几天"))
            and not any(term in text for term in ("现在", "当前", "实时"))
        )

    @staticmethod
    def _is_generic_weather_request(text: str) -> bool:
        return (
            any(term in text for term in ("天气怎么样", "天气如何", "天气情况", "天气咋样", "天气好吗"))
            and not any(term in text for term in ("今天", "今日", "现在", "当前", "实时", "明天", "后天"))
        )

    @staticmethod
    def _format_travel_answer(data: WeatherData) -> str:
        description = data.weather_description or "天气情况待确认"
        temperature = ""
        if data.temperature_min_c is not None and data.temperature_max_c is not None:
            temperature = f"，气温{data.temperature_min_c:g}～{data.temperature_max_c:g}°C"
        rain = f"，降雨概率{data.precipitation_probability_percent}%" if data.precipitation_probability_percent is not None else ""
        if not rain and data.precipitation_mm is not None:
            rain = f"，预计降水{data.precipitation_mm:g} mm"
        advice = "适合安排户外游览，建议根据体感准备饮水和防晒用品。"
        if data.precipitation_probability_percent is not None and data.precipitation_probability_percent >= 50:
            advice = "建议携带雨具，并准备室内或短途备用方案。"
        elif data.precipitation_mm is not None and data.precipitation_mm > 0:
            advice = "预计有降水，建议携带雨具，并准备室内或短途备用方案。"
        return f"{data.location}（{data.date}）{description}{temperature}{rain}。{advice}"

    @staticmethod
    def _is_weather_request(text: str) -> bool:
        return any(word in text for word in ("天气", "下雨", "温度", "湿度", "风速", "降雨", "旅游", "出行", "景点", "适合"))

    @staticmethod
    def _extract_query(text: str) -> WeatherQuery | None:
        cleaned = re.sub(r"[，。！？?！,.]", "", text).strip()
        normalized = re.sub(r"^(请问|帮我查一下|帮我查|查询|查一下|查)\s*", "", cleaned).strip()
        normalized = re.sub(r"(?:明天|后天|下周|最近|近期|近几天|这几天|这几日|未来几天|未来\s*[3３]\s*天|未来\s*[7７]\s*天|多日)", "", normalized).strip()
        match = re.search(r"(?:今天|今日|现在|当前|天气|会下雨|下雨)", normalized)
        location = normalized[: match.start()] if match else normalized
        location = location.strip()
        location = re.sub(r"(的)$", "", location).strip()
        if not location or location in {"今天", "今日", "现在", "当前"}:
            return None
        current = any(word in cleaned for word in ("现在", "当前"))
        forecast = (
            WeatherAgent._is_recent_forecast_request(cleaned)
            or WeatherAgent._is_generic_weather_request(cleaned)
            or any(word in cleaned for word in ("明天", "后天", "下周", "未来3天", "未来三天", "未来7天", "未来七天", "多日"))
        )
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
        elif data.precipitation_mm is not None:
            parts.append(f"预计降水{data.precipitation_mm:g} mm")
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
            elif day.precipitation_mm is not None:
                values.append(f"预计降水{day.precipitation_mm:g} mm")
            parts.append(f"{values[0]}：{'，'.join(values[1:])}")
        return "；".join(parts) + "。"
