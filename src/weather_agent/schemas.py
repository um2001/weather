from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeatherQuery(BaseModel):
    location: str = Field(min_length=1)
    date: Literal["current", "today"] = "today"
    unit: Literal["celsius"] = "celsius"
    metrics: list[str] = Field(default_factory=list)

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
    source: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)

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


class WeatherIntent(BaseModel):
    kind: Literal["weather", "unsupported", "other"]
    location: str | None = None
    date: Literal["current", "today"] = "today"
    metrics: list[str] = Field(default_factory=list)
