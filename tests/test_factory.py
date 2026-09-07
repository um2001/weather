from weather_agent import factory


def test_factory_reuses_api_host_for_geo_when_no_geo_host_is_configured(monkeypatch):
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("QWEATHER_API_KEY", "test-key")
    monkeypatch.setenv("QWEATHER_API_HOST", "https://custom.re.qweatherapi.com")
    monkeypatch.delenv("QWEATHER_GEO_HOST", raising=False)
    monkeypatch.setattr(factory, "QWeatherProvider", FakeProvider)
    monkeypatch.setattr(factory.OpenAICompatibleWeatherLLM, "from_env", classmethod(lambda cls: object()))

    factory.create_weather_agent()

    assert captured["api_host"] == "https://custom.re.qweatherapi.com"
    assert captured["geo_host"] == "https://custom.re.qweatherapi.com"
