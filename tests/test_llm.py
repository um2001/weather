import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from weather_agent.errors import ConfigurationError, LanguageModelError
from weather_agent.llm import OpenAICompatibleWeatherLLM
from weather_agent.schemas import ChatMessage, WeatherData


def test_llm_parses_json_intent_and_includes_history():
    captured = []

    def invoke(messages):
        captured.extend(messages)
        return AIMessage(content='```json\n{"kind":"weather","location":"上海","date":"today","metrics":[]}\n```')

    llm = OpenAICompatibleWeatherLLM(RunnableLambda(invoke))
    intent = llm.extract_intent(
        "上海",
        [ChatMessage(role="assistant", content="请告诉我城市。")],
    )

    assert intent.location == "上海"
    assert any(message.content == "请告诉我城市。" for message in captured)


def test_llm_rejects_invalid_intent_response():
    llm = OpenAICompatibleWeatherLLM(RunnableLambda(lambda messages: AIMessage(content="not json")))
    with pytest.raises(LanguageModelError):
        llm.extract_intent("上海天气", [])


def test_llm_answer_receives_only_standard_weather_data():
    captured = []

    def invoke(messages):
        captured.extend(messages)
        return AIMessage(content="上海今天24°C。")

    llm = OpenAICompatibleWeatherLLM(RunnableLambda(invoke))
    data = WeatherData(location="上海", date="today", temperature_c=24, source="fake")

    assert llm.generate_answer("穿什么？", [], data) == "上海今天24°C。"
    assert '"temperature_c":24.0' in captured[-1].content


def test_llm_requires_environment_configuration(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(ConfigurationError):
        OpenAICompatibleWeatherLLM.from_env()
