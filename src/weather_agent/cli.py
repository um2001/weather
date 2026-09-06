import logging
import os

import typer

from .agent import WeatherAgent
from .providers.wttr import WttrProvider

app = typer.Typer(add_completion=False, help="天气助手 Agent")


@app.command()
def chat() -> None:
    """启动命令行天气助手。"""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    agent = WeatherAgent(WttrProvider(timeout_seconds=float(os.getenv("WEATHER_TIMEOUT_SECONDS", "8"))))
    typer.echo("天气助手已启动，输入 quit 退出。")
    while True:
        try:
            text = typer.prompt("你")
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            break
        if text.strip().lower() in {"quit", "exit", "退出"}:
            break
        typer.echo(agent.answer(text))


def main() -> None:
    app()
