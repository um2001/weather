import os

from .agent import WeatherAgent
from .cache import WeatherCache
from .llm import OpenAICompatibleWeatherLLM
from .providers.qweather import QWeatherProvider


def create_weather_agent() -> WeatherAgent:
    api_key = os.getenv("QWEATHER_API_KEY")
    if not api_key:
        from .errors import ConfigurationError

        raise ConfigurationError("请配置 QWEATHER_API_KEY。")
    api_host = os.getenv("QWEATHER_API_HOST", "https://devapi.qweather.com")
    provider = QWeatherProvider(
        api_key=api_key,
        api_host=api_host,
        # A custom QWeather domain normally serves both weather and geo paths.
        # Keep a separate override for accounts that receive distinct hosts.
        geo_host=os.getenv("QWEATHER_GEO_HOST") or api_host,
        timeout_seconds=float(os.getenv("WEATHER_TIMEOUT_SECONDS", "8")),
    )
    return WeatherAgent(
        provider,
        language_model=OpenAICompatibleWeatherLLM.from_env(),
        cache=WeatherCache(ttl_seconds=float(os.getenv("WEATHER_CACHE_TTL_SECONDS", "120"))),
    )
