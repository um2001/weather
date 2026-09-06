import logging
import os
import re
from time import perf_counter
from typing import Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .errors import ConfigurationError, LanguageModelError
from .schemas import ChatMessage, WeatherData, WeatherIntent

logger = logging.getLogger(__name__)


class WeatherLanguageModel(Protocol):
    def extract_intent(self, message: str, history: list[ChatMessage]) -> WeatherIntent: ...

    def generate_answer(self, message: str, history: list[ChatMessage], data: WeatherData) -> str: ...


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
                "明天、后天、多日预报、长期气候等当前不支持，kind=unsupported。"
                "与天气无关则 kind=other。不要猜测历史中没有出现的地点。"
                "只返回 JSON，格式为："
                '{"kind":"weather|unsupported|other","location":"城市或null",'
                '"date":"current|today","metrics":[]}。'
            )
        )
        started = perf_counter()
        try:
            result = self.model.invoke([system, *self._history_messages(history), HumanMessage(content=message)])
            content = result.content
            if not isinstance(content, str):
                raise ValueError("intent response is not text")
            json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
            intent = WeatherIntent.model_validate_json(json_text)
        except Exception as exc:
            logger.warning(
                "language model intent extraction failed error=%s duration_ms=%.1f",
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise LanguageModelError("大模型暂时无法处理请求") from exc
        logger.info("language model intent extracted duration_ms=%.1f", (perf_counter() - started) * 1000)
        return intent

    def generate_answer(self, message: str, history: list[ChatMessage], data: WeatherData) -> str:
        system = SystemMessage(
            content=(
                "你是中文天气助手。只能根据提供的标准天气数据回答当前问题，"
                "不得补充或猜测数据中没有的信息。回答简洁、自然，并明确地点和日期。"
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
        return content.strip()

    @staticmethod
    def _history_messages(history: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
        return [
            HumanMessage(content=item.content) if item.role == "user" else AIMessage(content=item.content)
            for item in history
        ]
