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

FORECAST_PAYLOAD = {
    "weather": [
        {"date": "2026-09-06", "mintempC": "18", "maxtempC": "26", "hourly": [{"weatherDesc": [{"value": "Sunny"}], "chanceofrain": "10"}]},
        {"date": "2026-09-07", "mintempC": "19", "maxtempC": "27", "hourly": [{"weatherDesc": [{"value": "Cloudy"}], "chanceofrain": "30"}]},
        {"date": "2026-09-08", "mintempC": "20", "maxtempC": "28", "hourly": [{"weatherDesc": [{"value": "Rain"}], "chanceofrain": "60"}]},
    ]
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


@respx.mock
def test_wttr_provider_parses_forecast():
    route = respx.get("https://wttr.in/上海", params={"format": "j1"}).mock(
        return_value=httpx.Response(200, json=FORECAST_PAYLOAD)
    )
    data = WttrProvider().get_forecast(WeatherQuery(location="上海", date="forecast", days=3))
    assert route.called
    assert len(data.days) == 3
    assert data.days[0].temperature_max_c == 26
    assert data.days[2].precipitation_probability_percent == 60
