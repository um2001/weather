from weather_agent.database import ConversationStore


def test_conversation_store_persists_messages(tmp_path):
    store = ConversationStore(str(tmp_path / "weather.db"))
    conversation = store.create()
    store.add_message(conversation["id"], "user", "后天去颐和园")
    store.add_message(conversation["id"], "assistant", "适合出行", {"source": "QWeather"})
    loaded = store.get(conversation["id"])
    assert loaded["title"] == "后天去颐和园"
    assert loaded["messages"][1]["weather"]["source"] == "QWeather"
