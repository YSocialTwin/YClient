import json
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stub_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _identity_decorator(func=None, **kwargs):
    if func is None:
        return lambda inner: inner
    return func


def _load_base_agent_module():
    preserved = {
        name: sys.modules.get(name)
        for name in (
            "y_client",
            "y_client.recsys",
            "y_client.news_feeds",
            "y_client.classes",
            "y_client.recsys.ContentRecSys",
            "y_client.recsys.FollowRecSys",
            "y_client.news_feeds.client_modals",
            "y_client.classes.annotator",
            "y_client.logger",
            "y_client.news_feeds.feed_reader",
            "y_client.classes.time",
            "y_client.memory_runtime",
            "y_client.llm",
            "yclient_memory.contracts",
            "sqlalchemy",
            "sqlalchemy.sql",
            "sqlalchemy.sql.expression",
        )
    }
    _stub_module("y_client", __path__=[str(ROOT / "y_client")])
    _stub_module("y_client.recsys", __path__=[])
    _stub_module("y_client.news_feeds", __path__=[])
    _stub_module("y_client.classes", __path__=[])
    _stub_module("y_client.recsys.ContentRecSys", ContentRecSys=type("ContentRecSys", (), {}))
    _stub_module("y_client.recsys.FollowRecSys", FollowRecSys=type("FollowRecSys", (), {}))
    _stub_module(
        "y_client.news_feeds.client_modals",
        Websites=type("Websites", (), {}),
        Images=type("Images", (), {}),
        Articles=type("Articles", (), {}),
        base=object(),
        get_engine=lambda: None,
        get_session=lambda: None,
        initialize_client_db=lambda **kwargs: None,
        session=None,
        Agent_Custom_Prompt=type("Agent_Custom_Prompt", (), {}),
        ImagePosts=type("ImagePosts", (), {}),
    )
    _stub_module("y_client.classes.annotator", Annotator=type("Annotator", (), {}))
    _stub_module("y_client.logger", log_execution_time=_identity_decorator)
    _stub_module("y_client.news_feeds.feed_reader", NewsFeed=type("NewsFeed", (), {}))
    _stub_module("y_client.classes.time", SimulationSlot=type("SimulationSlot", (), {}))
    _stub_module("y_client.memory_runtime", build_agent_memory_engine=lambda *args, **kwargs: None)
    _stub_module(
        "y_client.llm",
        AssistantAgent=type("AssistantAgent", (), {}),
        MultimodalConversableAgent=type("MultimodalConversableAgent", (), {}),
    )
    _stub_module(
        "yclient_memory.contracts",
        BrowseMemoryRequest=type("BrowseMemoryRequest", (), {}),
        CommentMemoryEvent=type("CommentMemoryEvent", (), {}),
        PostMemoryEvent=type("PostMemoryEvent", (), {}),
        PostStyleRequest=type("PostStyleRequest", (), {}),
        ReplyMemoryRequest=type("ReplyMemoryRequest", (), {}),
        VoteMemoryEvent=type("VoteMemoryEvent", (), {}),
    )
    _stub_module("sqlalchemy", text=lambda value: value, or_=lambda *args: args)
    _stub_module("sqlalchemy.sql", __path__=[])
    _stub_module("sqlalchemy.sql.expression", func=object())

    module_name = "microblog_opinion_dynamics_base_agent_under_test"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / "y_client" / "classes" / "base_agent.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    for name, original in preserved.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original
    return module


base_agent_module = _load_base_agent_module()
Agent = base_agent_module.Agent


def _bare_agent():
    ag = Agent.__new__(Agent)
    ag.user_id = 7
    ag.name = "tester"
    ag.is_page = 0
    ag.interests = ["topic a", "topic b"]
    ag.opinions = {}
    ag.opinions_enabled = True
    ag.opinion_dynamics = {
        "enabled": True,
        "model_name": "bounded_confidence",
        "opinion_groups": {
            "Strongly against": [0.0, 0.2],
            "Against": [0.2, 0.4],
            "Neutral": [0.4, 0.6],
            "In favor": [0.6, 0.8],
            "Strongly in favor": [0.8, 1.0],
        },
        "parameters": {
            "epsilon": 0.5,
            "mu": 0.5,
            "theta": 0.1,
            "cold_start": "neutral",
        },
    }
    ag.base_url = "http://example.test"
    ag.joined_on = 1
    ag.stubborn_topics = set()
    ag.custom_features = {}
    return ag


def test_seed_initial_opinions_includes_stubborn_topics(monkeypatch):
    ag = _bare_agent()
    ag.opinions = {"topic a": 0.8, "topic b": 0.2}
    ag.stubborn_topics = {"topic a"}

    calls = []

    class _Resp:
        def __init__(self, payload):
            self.__dict__["_content"] = json.dumps(payload).encode("utf-8")

    def _fake_post(url, headers=None, data=None):
        payload = json.loads(data)
        calls.append((url, payload))
        if url.endswith("/get_user_opinions"):
            return _Resp({})
        if url.endswith("/set_user_opinions"):
            return _Resp({"status": 200})
        raise AssertionError(url)

    monkeypatch.setattr(base_agent_module, "post", _fake_post)
    ag._seed_initial_opinions_if_needed()

    assert calls[1][1]["stubborn_topics"] == ["topic a"]


def test_new_opinions_skips_stubborn_topics(monkeypatch):
    ag = _bare_agent()
    ag.opinions = {"topic a": 0.2}
    ag.stubborn_topics = {"topic a"}

    writes = []

    class _Resp:
        def __init__(self, payload):
            self.__dict__["_content"] = json.dumps(payload).encode("utf-8")

    def _fake_get(url, headers=None, data=None):
        payload = json.loads(data)
        if url.endswith("/get_post_topics"):
            return _Resp([1])
        if url.endswith("/get_post_author"):
            return _Resp({"user_id": 2})
        raise AssertionError(url)

    def _fake_post(url, headers=None, data=None):
        payload = json.loads(data)
        if url.endswith("/get_user_opinions"):
            if payload["user_id"] == 2:
                return _Resp({"topic a": [0.6, 1]})
            return _Resp({"topic a": [0.2, 1]})
        if url.endswith("/set_user_opinions"):
            writes.append(payload)
            return _Resp({"status": 200})
        raise AssertionError(url)

    monkeypatch.setattr(base_agent_module, "get", _fake_get)
    monkeypatch.setattr(base_agent_module, "post", _fake_post)
    ag.new_opinions(post_id=99, tid=5, text="reply")

    assert ag.opinions["topic a"] == 0.2
    assert writes == [
        {
            "user_id": 7,
            "opinions": {"1": 0.2},
            "id_post": 99,
            "id_interacted_with": 2,
            "round": 5,
            "stubborn_topics": ["topic a"],
        }
    ]
