import logging
import os

import typer

from .errors import ConfigurationError
from .factory import create_weather_agent
from .schemas import ChatMessage

app = typer.Typer(add_completion=False, help="天气助手 Agent")


@app.command()
def chat() -> None:
    """启动命令行天气助手。"""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    try:
        agent = create_weather_agent()
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("天气助手已启动，输入 quit 退出。")
    history: list[ChatMessage] = []
    while True:
        try:
            text = typer.prompt("你")
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            break
        if text.strip().lower() in {"quit", "exit", "退出"}:
            break
        reply = agent.answer(text, history)
        typer.echo(reply)
        history.extend(
            [
                ChatMessage(role="user", content=text),
                ChatMessage(role="assistant", content=reply),
            ]
        )


def main() -> None:
    app()
