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
