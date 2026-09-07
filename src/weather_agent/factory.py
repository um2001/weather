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
    provider = QWeatherProvider(
        api_key=api_key,
        api_host=os.getenv("QWEATHER_API_HOST", "https://devapi.qweather.com"),
        geo_host=os.getenv("QWEATHER_GEO_HOST", "https://geoapi.qweather.com"),
        timeout_seconds=float(os.getenv("WEATHER_TIMEOUT_SECONDS", "8")),
    )
    return WeatherAgent(
        provider,
        language_model=OpenAICompatibleWeatherLLM.from_env(),
        cache=WeatherCache(ttl_seconds=float(os.getenv("WEATHER_CACHE_TTL_SECONDS", "120"))),
    )
