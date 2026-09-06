import httpx
import respx

from weather_agent.providers.qweather import QWeatherProvider
from weather_agent.schemas import WeatherQuery


@respx.mock
def test_qweather_provider_normalizes_today_response():
    respx.get("https://geoapi.qweather.com/geo/v2/city/lookup").mock(
        return_value=httpx.Response(200, json={"code": "200", "location": [{"id": "101010100"}]})
    )
    respx.get("https://devapi.qweather.com/v7/weather/3d").mock(
        return_value=httpx.Response(200, json={"code": "200", "daily": [{"fxDate": "2026-09-06", "tempMin": "21", "tempMax": "29", "textDay": "多云", "precipProbability": "20", "windDirDay": "东南风", "windScaleDay": "2"}]})
    )
    data = QWeatherProvider("test-key").get_weather(WeatherQuery(location="北京", target_date="2026-09-06"))
    assert data.temperature_min_c == 21
    assert data.temperature_max_c == 29
    assert data.source == "QWeather"


@respx.mock
def test_qweather_provider_parses_current_response():
    respx.get("https://geoapi.qweather.com/geo/v2/city/lookup").mock(
        return_value=httpx.Response(200, json={"code": "200", "location": [{"id": "101020100"}]})
    )
    respx.get("https://devapi.qweather.com/v7/weather/now").mock(
        return_value=httpx.Response(200, json={"code": "200", "now": {"temp": "24", "text": "晴", "humidity": "45", "windSpeed": "10", "windDir": "东风", "windScale": "2"}})
    )
    data = QWeatherProvider("test-key").get_weather(WeatherQuery(location="上海", date="current"))
    assert data.temperature_c == 24
    assert data.humidity_percent == 45
    assert data.wind_description == "东风 2级"
