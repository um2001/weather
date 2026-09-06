import httpx
import pytest
import respx

from weather_agent.errors import WeatherDataInvalid, WeatherServiceUnavailable
from weather_agent.providers.wttr import WttrProvider
from weather_agent.schemas import WeatherQuery


PAYLOAD = {
    "current_condition": [{"temp_C": "21", "weatherDesc": [{"value": "Partly cloudy"}], "humidity": "55", "windspeedKmph": "13"}],
    "weather": [{"hourly": [{"chanceofrain": "30"}]}],
}


@respx.mock
def test_wttr_provider_normalizes_response():
    respx.get("https://wttr.in/上海").mock(return_value=httpx.Response(200, json=PAYLOAD))
    data = WttrProvider().get_weather(WeatherQuery(location="上海"))
    assert data.temperature_c == 21
    assert data.humidity_percent == 55
    assert data.precipitation_probability_percent == 30
    assert data.source == "wttr.in"


@respx.mock
def test_wttr_provider_maps_http_failure():
    respx.get("https://wttr.in/上海").mock(return_value=httpx.Response(503))
    with pytest.raises(WeatherServiceUnavailable):
        WttrProvider().get_weather(WeatherQuery(location="上海"))


@respx.mock
def test_wttr_provider_maps_invalid_payload():
    respx.get("https://wttr.in/上海").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(WeatherDataInvalid):
        WttrProvider().get_weather(WeatherQuery(location="上海"))
