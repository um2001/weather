import json
from pathlib import Path


def test_vscode_launch_configuration_loads_local_env_file():
    root = Path(__file__).parents[1]
    config = json.loads((root / ".vscode" / "launch.json").read_text(encoding="utf-8"))

    assert config["configurations"][0]["envFile"] == "${workspaceFolder}/.env"
    assert (root / ".env.example").is_file()
