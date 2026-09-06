import os

from .agent import WeatherAgent
from .cache import WeatherCache
from .llm import OpenAICompatibleWeatherLLM
from .providers.wttr import WttrProvider


def create_weather_agent() -> WeatherAgent:
    provider = WttrProvider(timeout_seconds=float(os.getenv("WEATHER_TIMEOUT_SECONDS", "8")))
    return WeatherAgent(
        provider,
        language_model=OpenAICompatibleWeatherLLM.from_env(),
        cache=WeatherCache(ttl_seconds=float(os.getenv("WEATHER_CACHE_TTL_SECONDS", "120"))),
    )
