from typer.testing import CliRunner

from weather_agent import cli


def test_cli_chat_can_exit(monkeypatch):
    class FakeAgent:
        def answer(self, text):
            return f"已查询：{text}"

    monkeypatch.setattr(cli, "WeatherAgent", lambda provider: FakeAgent())
    result = CliRunner().invoke(cli.app, [], input="上海天气\n退出\n")
    assert result.exit_code == 0
    assert "已查询：上海天气" in result.stdout
