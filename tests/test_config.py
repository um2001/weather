from weather_agent.config import load_local_env


def test_load_local_env_reads_unset_values(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("QWEATHER_API_KEY=weather-key\nLLM_MODEL='test-model'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    load_local_env()

    assert __import__("os").environ["QWEATHER_API_KEY"] == "weather-key"
    assert __import__("os").environ["LLM_MODEL"] == "test-model"


def test_load_local_env_keeps_explicit_environment_value(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("LLM_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_MODEL", "shell-model")

    load_local_env()

    assert __import__("os").environ["LLM_MODEL"] == "shell-model"
