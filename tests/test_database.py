from weather_agent.database import ConversationStore


def test_conversation_store_persists_messages(tmp_path):
    store = ConversationStore(str(tmp_path / "weather.db"))
    conversation = store.create()
    store.add_message(conversation["id"], "user", "后天去颐和园")
    store.add_message(conversation["id"], "assistant", "适合出行", {"source": "QWeather"})
    loaded = store.get(conversation["id"])
    assert loaded["title"] == "后天去颐和园"
    assert loaded["messages"][1]["weather"]["source"] == "QWeather"


def test_default_database_path_is_inside_package(monkeypatch):
    monkeypatch.delenv("WEATHER_DB_PATH", raising=False)
    store = ConversationStore()
    assert store.path.name == "weather_agent.db"
    assert store.path.parent.name == "weather_agent"


def test_delete_removes_conversation_messages(tmp_path):
    store = ConversationStore(str(tmp_path / "weather.db"))
    conversation = store.create()
    store.add_message(conversation["id"], "user", "上海")
    assert store.delete(conversation["id"])
    with store._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation["id"],)).fetchone()[0] == 0
