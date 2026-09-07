from weather_agent.agent import WeatherAgent
from weather_agent.errors import LanguageModelError, WeatherServiceUnavailable
from weather_agent.schemas import ChatMessage, WeatherData, WeatherIntent


class FakeProvider:
    def __init__(self, error=False):
        self.error = error
        self.queries = []

    def get_weather(self, query):
        self.queries.append(query)
        if self.error:
            raise WeatherServiceUnavailable()
        return WeatherData(location=query.location, date=query.date, temperature_c=22, weather_description="晴", precipitation_probability_percent=10, source="fake")

    def get_forecast(self, query):
        from weather_agent.schemas import DailyForecast, ForecastData

        return ForecastData(
            location=query.location,
            timezone=query.timezone,
            days=[DailyForecast(date="2026-09-06", temperature_min_c=18, temperature_max_c=26, weather_description="晴")],
            source="fake",
        )


class PoiProvider(FakeProvider):
    def resolve_place(self, name, city=None):
        from weather_agent.providers.qweather import GeocodedPlace

        return GeocodedPlace(name=name, city=city, latitude=31.1, longitude=121.6, timezone="Asia/Shanghai")


class FailingPoiProvider(FakeProvider):
    def resolve_place(self, name, city=None):
        raise AssertionError("ordinary city weather must not use POI geocoding")


def test_agent_calls_weather_tool_and_answers_in_chinese():
    provider = FakeProvider()
    answer = WeatherAgent(provider).answer("上海今天会下雨吗？")
    assert provider.queries[0].location == "上海"
    assert "上海" in answer and "22°C" in answer and "降雨概率10%" in answer


def test_agent_asks_for_location_when_missing():
    provider = FakeProvider()
    assert "城市或地区" in WeatherAgent(provider).answer("今天会下雨吗？")
    assert provider.queries == []


def test_agent_does_not_fabricate_when_service_fails():
    answer = WeatherAgent(FakeProvider(error=True)).answer("北京天气怎么样")
    assert "暂时无法使用" in answer
    assert "°C" not in answer


def test_agent_rejects_future_forecast_without_calling_provider():
    provider = FakeProvider()
    response = WeatherAgent(provider).respond("北京长期气候怎么样")

    assert response.status == "unsupported"
    assert provider.queries == []


def test_agent_returns_forecast_without_language_model():
    response = WeatherAgent(FakeProvider()).respond("北京未来3天天气")

    assert response.status == "success"
    assert "未来1天天气预报" in response.reply
    assert "北京" in response.reply


class FakeLanguageModel:
    def __init__(self, intent):
        self.intent = intent
        self.answer_calls = []

    def extract_intent(self, message, history):
        self.extract_call = (message, history)
        return self.intent

    def generate_answer(self, message, history, data):
        self.answer_calls.append((message, history, data))
        return f"模型回答：{data.location}{data.temperature_c:g}°C"


def test_agent_uses_model_to_understand_natural_language():
    provider = FakeProvider()
    model = FakeLanguageModel(WeatherIntent(kind="weather", location="杭州", metrics=["temperature"]))

    response = WeatherAgent(provider, language_model=model).respond("出门穿厚点还是薄点？")

    assert response.status == "success"
    assert response.reply == "模型回答：杭州22°C"
    assert provider.queries[0].location == "杭州"


def test_agent_does_not_geocode_ordinary_city_weather_as_poi():
    provider = FailingPoiProvider()
    model = FakeLanguageModel(WeatherIntent(kind="weather", location="哈尔滨"))

    response = WeatherAgent(provider, language_model=model).respond("哈尔滨最近天气怎么样？")

    assert response.status == "success"
    assert provider.queries[0].location == "哈尔滨"


def test_agent_uses_provider_geocoding_for_arbitrary_attraction():
    provider = PoiProvider()
    model = FakeLanguageModel(WeatherIntent(kind="travel", location="上海", attraction="上海迪士尼度假区", target_date="2026-09-09"))
    response = WeatherAgent(provider, language_model=model).respond("后天去上海迪士尼度假区")

    assert response.status == "success"
    assert provider.queries[0].location == "上海迪士尼度假区"
    assert provider.queries[0].latitude == 31.1


def test_agent_passes_history_to_model_for_follow_up_location():
    provider = FakeProvider()
    model = FakeLanguageModel(WeatherIntent(kind="weather", location="上海"))
    history = [
        ChatMessage(role="user", content="今天会下雨吗？"),
        ChatMessage(role="assistant", content="请告诉我想查询的城市或地区。"),
    ]

    response = WeatherAgent(provider, language_model=model).respond("上海", history)

    assert response.status == "success"
    assert model.extract_call == ("上海", history)


def test_agent_asks_for_location_from_model_intent():
    provider = FakeProvider()
    model = FakeLanguageModel(WeatherIntent(kind="weather", location=None))

    response = WeatherAgent(provider, language_model=model).respond("今天适合出门吗？")

    assert response.status == "clarification"
    assert provider.queries == []


def test_agent_does_not_call_weather_provider_for_non_weather_intent():
    provider = FailingPoiProvider()
    model = FakeLanguageModel(WeatherIntent(kind="other"))

    response = WeatherAgent(provider, language_model=model).respond("给我讲个笑话")

    assert response.status == "unsupported"
    assert provider.queries == []


def test_agent_falls_back_to_standardized_data_when_answer_model_fails():
    class FailingAnswerModel(FakeLanguageModel):
        def generate_answer(self, message, history, data):
            raise LanguageModelError()

    model = FailingAnswerModel(WeatherIntent(kind="weather", location="北京"))
    response = WeatherAgent(FakeProvider(), language_model=model).respond("北京冷不冷？")

    assert response.status == "success"
    assert "北京" in response.reply and "22°C" in response.reply


def test_agent_supports_travel_date_and_returns_weather_payload():
    provider = FakeProvider()
    response = WeatherAgent(provider).respond("后天去颐和园旅游适合吗？")

    assert response.status == "success"
    assert provider.queries[0].location == "北京"
    assert provider.queries[0].target_date is not None
    assert response.weather is not None
