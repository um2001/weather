import logging
import json
import os
import re
from time import perf_counter
from typing import Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .errors import ConfigurationError, LanguageModelError, LanguageModelResponseError
from .schemas import ChatMessage, ForecastData, WeatherData, WeatherIntent

logger = logging.getLogger(__name__)


class WeatherLanguageModel(Protocol):
    def extract_intent(self, message: str, history: list[ChatMessage]) -> WeatherIntent: ...

    def generate_answer(self, message: str, history: list[ChatMessage], data: WeatherData | ForecastData) -> str: ...


class OpenAICompatibleWeatherLLM:
    def __init__(self, model: ChatOpenAI):
        self.model = model

    @classmethod
    def from_env(cls) -> "OpenAICompatibleWeatherLLM":
        api_key = os.getenv("LLM_API_KEY")
        model_name = os.getenv("LLM_MODEL")
        if not api_key or not model_name:
            raise ConfigurationError("请配置 LLM_API_KEY 和 LLM_MODEL。")
        return cls(
            ChatOpenAI(
                api_key=api_key,
                model=model_name,
                base_url=os.getenv("LLM_BASE_URL") or None,
                temperature=0,
                timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
            )
        )

    def extract_intent(self, message: str, history: list[ChatMessage]) -> WeatherIntent:
        system = SystemMessage(
            content=(
                "你是天气查询意图解析器。结合对话历史判断当前用户消息。"
                "kind=weather 表示查询当前或今天的城市天气；缺少地点时 location=null。"
                "明天、后天、多日预报可用 kind=weather 且 date=forecast；长期气候等当前不支持。"
                "与天气无关则 kind=other。不要猜测历史中没有出现的地点。"
                "只返回 JSON，格式为："
                '{"kind":"weather|unsupported|other","location":"城市或null",'
                '"date":"current|today|forecast","days":3,"metrics":[]}。'
            )
        )
        started = perf_counter()
        content = ""
        try:
            result = self.model.invoke([system, *self._history_messages(history), HumanMessage(content=message)])
            content = result.content
            if not isinstance(content, str):
                raise ValueError("intent response is not text")
        except Exception as exc:
            logger.warning(
                "language model intent extraction failed error=%s detail=%s response_preview=%s duration_ms=%.1f",
                type(exc).__name__,
                str(exc)[:240],
                content[:240].replace("\n", " ") if isinstance(content, str) else "<non-text>",
                (perf_counter() - started) * 1000,
            )
            raise LanguageModelError("大模型暂时无法处理请求") from exc
        try:
            intent = self._parse_intent(content)
        except Exception as exc:
            logger.warning(
                "language model intent response invalid error=%s detail=%s response_preview=%s duration_ms=%.1f",
                type(exc).__name__,
                str(exc)[:240],
                content[:240].replace("\n", " "),
                (perf_counter() - started) * 1000,
            )
            raise LanguageModelResponseError("大模型返回的查询格式无法识别") from exc
        logger.info("language model intent extracted duration_ms=%.1f", (perf_counter() - started) * 1000)
        return intent

    @staticmethod
    def _parse_intent(content: str) -> WeatherIntent:
        """Parse common model JSON variants without weakening schema validation."""
        text = content.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise ValueError("intent response does not contain a JSON object")
            text = match.group(0)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("intent response is not a JSON object")
        kind_aliases = {
            "天气": "weather",
            "天气查询": "weather",
            "weather_query": "weather",
            "weather-query": "weather",
            "不支持": "unsupported",
            "其他": "other",
        }
        date_aliases = {
            "现在": "current",
            "当前": "current",
            "today": "today",
            "今天": "today",
            "明天": "forecast",
            "明日": "forecast",
            "tomorrow": "forecast",
            "后天": "forecast",
            "forecast": "forecast",
            "预报": "forecast",
        }
        if isinstance(payload.get("kind"), str):
            payload["kind"] = kind_aliases.get(payload["kind"], payload["kind"])
        if isinstance(payload.get("date"), str):
            payload["date"] = date_aliases.get(payload["date"], payload["date"])
        if payload.get("date") == "forecast":
            try:
                days = payload.get("days", 3)
                if isinstance(days, str):
                    days = re.search(r"\d+", days).group(0) if re.search(r"\d+", days) else 3
                payload["days"] = max(3, min(7, int(days)))
            except (TypeError, ValueError):
                payload["days"] = 3
        if payload.get("metrics") is None:
            payload["metrics"] = []
        return WeatherIntent.model_validate(payload)

    def generate_answer(self, message: str, history: list[ChatMessage], data: WeatherData) -> str:
        system = SystemMessage(
            content=(
                "你是中文天气助手。只能根据提供的标准天气数据回答当前问题，"
                "不得补充或猜测数据中没有的信息。回答简洁、自然，并明确地点和日期。"
                "只输出最终回答，不要输出<think>、Markdown代码块或分析过程。"
            )
        )
        prompt = HumanMessage(content=f"用户问题：{message}\n天气数据：{data.model_dump_json()}")
        started = perf_counter()
        try:
            result = self.model.invoke([system, *self._history_messages(history), prompt])
        except Exception as exc:
            logger.warning(
                "language model answer generation failed error=%s duration_ms=%.1f",
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise LanguageModelError("大模型暂时无法生成回答") from exc
        content = result.content
        if not isinstance(content, str) or not content.strip():
            raise LanguageModelError("大模型返回了空回答")
        logger.info("language model answer generated duration_ms=%.1f", (perf_counter() - started) * 1000)
        return self._clean_answer(content)

    @staticmethod
    def _clean_answer(content: str) -> str:
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"^```(?:text|markdown)?\s*|\s*```$", "", cleaned.strip(), flags=re.IGNORECASE)
        return cleaned.strip()

    @staticmethod
    def _history_messages(history: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
        return [
            HumanMessage(content=item.content) if item.role == "user" else AIMessage(content=item.content)
            for item in history
        ]
