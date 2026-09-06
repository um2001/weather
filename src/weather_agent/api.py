import logging
import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request

from .agent import WeatherAgent
from .errors import ConfigurationError
from .factory import create_weather_agent
from .schemas import ChatRequest, ChatResponse

app = FastAPI(title="天气助手 API", version="0.2.0")


def get_agent(request: Request) -> WeatherAgent:
    agent = getattr(request.app.state, "weather_agent", None)
    if agent is None:
        try:
            agent = create_weather_agent()
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        request.app.state.weather_agent = agent
    return agent


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, agent: WeatherAgent = Depends(get_agent)) -> ChatResponse:
    return agent.respond(payload.message, payload.history)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    uvicorn.run(
        "weather_agent.api:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
    )
