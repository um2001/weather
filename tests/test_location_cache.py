from weather_agent.cache import WeatherCache
from weather_agent.location import resolve_attraction, resolve_location
from weather_agent.schemas import WeatherData, WeatherQuery


def test_location_alias_is_normalized_with_timezone():
    resolved = resolve_location("魔都")
    assert resolved.name == "上海"
    assert resolved.timezone == "Asia/Shanghai"


def test_attraction_is_mapped_to_city():
    resolved = resolve_location("颐和园")
    assert resolved.name == "北京"


def test_known_attraction_can_be_checked_without_guessing_unknown_places():
    assert resolve_attraction("西湖").name == "杭州"
    assert resolve_attraction("同名公园") is None


def test_weather_cache_reuses_value_until_ttl():
    cache = WeatherCache(ttl_seconds=60)
    calls = []

    def load():
        calls.append(1)
        return WeatherData(location="上海", date="today", source="fake")

    query = WeatherQuery(location="上海")
    cache.get_or_set(query, load)
    cache.get_or_set(query, load)
    assert len(calls) == 1
