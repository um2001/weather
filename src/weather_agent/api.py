import logging
import os
from time import perf_counter

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import WeatherAgent
from .errors import ConfigurationError
from .factory import create_weather_agent
from .database import ConversationStore
from .schemas import ChatMessage, ChatRequest, ChatResponse

app = FastAPI(title="天气助手 API", version="0.2.0")
logger = logging.getLogger(__name__)
WEB_INDEX = os.path.join(os.path.dirname(__file__), "web", "index.html")
app.mount("/web", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "web")), name="web")
store = ConversationStore()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    logger.info(
        "api request method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started) * 1000,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(WEB_INDEX, media_type="text/html")


def get_agent(request: Request) -> WeatherAgent:
    agent = getattr(request.app.state, "weather_agent", None)
    if agent is None:
        try:
            agent = create_weather_agent()
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        request.app.state.weather_agent = agent
    return agent


@app.post("/api/chat", response_model=ChatResponse, response_model_exclude_none=True)
def chat(payload: ChatRequest, agent: WeatherAgent = Depends(get_agent)) -> ChatResponse:
    conversation = store.get(payload.conversation_id) if payload.conversation_id else None
    if payload.conversation_id and conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    history = payload.history
    if conversation is not None:
        history = [ChatMessage(role=item["role"], content=item["content"]) for item in conversation["messages"]]
    response = agent.respond(payload.message, history)
    conversation = conversation or store.create()
    store.add_message(conversation["id"], "user", payload.message)
    store.add_message(conversation["id"], "assistant", response.reply, response.weather.model_dump() if response.weather else None)
    return response


@app.get("/api/conversations")
def list_conversations() -> list[dict]:
    return store.list()


@app.post("/api/conversations")
def create_conversation() -> dict:
    return store.create()


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: int) -> dict:
    conversation = store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int) -> dict[str, bool]:
    if not store.delete(conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"deleted": True}


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    uvicorn.run(
        "weather_agent.api:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
    )
