from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeatherQuery(BaseModel):
    location: str = Field(min_length=1)
    date: Literal["current", "today", "forecast"] = "today"
    unit: Literal["celsius"] = "celsius"
    metrics: list[str] = Field(default_factory=list)
    days: int = Field(default=3, ge=3, le=7)
    timezone: str | None = None
    target_date: str | None = None

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("location cannot be blank")
        return value


class WeatherData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str
    date: str
    temperature_c: float | None = None
    weather_description: str | None = None
    humidity_percent: int | None = Field(default=None, ge=0, le=100)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
    precipitation_probability_percent: int | None = Field(default=None, ge=0, le=100)
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    wind_description: str | None = None
    source: str
    timezone: str | None = None


class DailyForecast(BaseModel):
    date: str
    weather_description: str | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_probability_percent: int | None = Field(default=None, ge=0, le=100)


class ForecastData(BaseModel):
    location: str
    timezone: str | None = None
    days: list[DailyForecast]
    source: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    conversation_id: int | None = None

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value


class ChatResponse(BaseModel):
    reply: str
    status: Literal["success", "clarification", "unsupported", "error"]
    weather: WeatherData | ForecastData | None = None


class WeatherIntent(BaseModel):
    kind: Literal["weather", "travel", "unsupported", "other"]
    location: str | None = None
    attraction: str | None = None
    attractions: list[str] = Field(default_factory=list)
    date: Literal["current", "today", "forecast"] = "today"
    metrics: list[str] = Field(default_factory=list)
    # For current/today queries the model may return 1; forecast is normalized to 3..7 by the agent.
    days: int = Field(default=3, ge=1, le=7)
    target_date: str | None = None
    target_date: str | None = None
