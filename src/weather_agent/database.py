import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConversationStore:
    def __init__(self, path: str | None = None):
        default_path = Path(__file__).with_name("weather_agent.db")
        self.path = Path(path or os.getenv("WEATHER_DB_PATH") or default_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    weather_json TEXT,
                    created_at TEXT NOT NULL
                );
            """)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, title: str = "新会话") -> dict[str, Any]:
        now = self._now()
        with self._connect() as db:
            cursor = db.execute("INSERT INTO conversations(title, created_at, updated_at) VALUES (?, ?, ?)", (title, now, now))
            conversation_id = cursor.lastrowid
        return {"id": conversation_id, "title": title, "created_at": now, "updated_at": now}

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC")]

    def get(self, conversation_id: int) -> dict[str, Any] | None:
        with self._connect() as db:
            conversation = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if conversation is None:
                return None
            messages = []
            for row in db.execute("SELECT role, content, weather_json, created_at FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)):
                item = dict(row)
                item["weather"] = json.loads(item.pop("weather_json")) if item["weather_json"] else None
                messages.append(item)
            result = dict(conversation)
            result["messages"] = messages
            return result

    def add_message(self, conversation_id: int, role: str, content: str, weather: Any = None) -> None:
        now = self._now()
        with self._connect() as db:
            db.execute("INSERT INTO messages(conversation_id, role, content, weather_json, created_at) VALUES (?, ?, ?, ?, ?)", (conversation_id, role, content, json.dumps(weather, ensure_ascii=False) if weather else None, now))
            db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            if role == "user":
                db.execute("UPDATE conversations SET title = ? WHERE id = ? AND title = '新会话'", (content[:28], conversation_id))

    def delete(self, conversation_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0
