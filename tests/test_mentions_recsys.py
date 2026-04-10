import json
import importlib

from y_client.recsys.ContentRecSys import ContentRecSys


def test_read_mentions_includes_user_id(monkeypatch):
    captured = {}

    class DummyResponse:
        def __init__(self):
            self.__dict__["_content"] = b"{}"

    def fake_post(url, headers=None, data=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json.loads(data)
        return DummyResponse()

    content_recsys_module = importlib.import_module("y_client.recsys.ContentRecSys")
    monkeypatch.setattr(content_recsys_module, "post", fake_post)

    recsys = ContentRecSys()
    recsys.read_mentions("http://localhost:5000", user_id=42)

    assert captured["url"] == "http://localhost:5000/read_mentions"
    assert captured["payload"]["uid"] == 42
