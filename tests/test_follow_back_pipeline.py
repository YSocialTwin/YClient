from types import SimpleNamespace

from y_client.classes import base_agent as base_agent_module
from y_client.classes.base_agent import Agent
from y_client.classes.fake_base_agent import FakeAgent


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_follow_dispatches_reciprocal_event(monkeypatch):
    posted = []

    def _fake_post(url, headers=None, data=None):
        posted.append((url, headers, data))
        return _Response({"status": 200})

    monkeypatch.setattr(base_agent_module, "post", _fake_post)

    dispatched = []
    agent = Agent.__new__(Agent)
    agent.user_id = 7
    agent.base_url = "http://example.test"
    agent.simulation_client = SimpleNamespace(
        process_reciprocal_follow_event=lambda **kwargs: dispatched.append(kwargs)
    )

    agent.follow(tid=4, target=11, action="follow")

    assert posted and posted[0][0] == "http://example.test/follow"
    assert dispatched == [
        {
            "actor_agent": agent,
            "target_user_id": 11,
            "action": "follow",
            "tid": 4,
        }
    ]


def test_handle_reciprocal_follow_event_applies_only_when_reverse_edge_missing():
    agent = Agent.__new__(Agent)
    agent.user_id = 11
    agent._check_follow_relationship = lambda follower_id, user_id: False
    agent._should_reciprocate_follow_event = lambda source_agent, action: True

    applied = []
    agent.follow = lambda **kwargs: applied.append(kwargs)

    result = agent.handle_reciprocal_follow_event(
        SimpleNamespace(user_id=7), "follow", tid=8
    )

    assert result is True
    assert applied == [
        {"tid": 8, "target": 7, "action": "follow", "reciprocal_check": False}
    ]


def test_handle_reciprocal_follow_event_skips_when_reverse_edge_already_exists():
    agent = Agent.__new__(Agent)
    agent.user_id = 11
    agent._check_follow_relationship = lambda follower_id, user_id: True
    agent._should_reciprocate_follow_event = lambda source_agent, action: True
    agent.follow = lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected"))

    result = agent.handle_reciprocal_follow_event(
        SimpleNamespace(user_id=7), "follow", tid=8
    )

    assert result is False


def test_secondary_follow_evaluation_triggers_reciprocal_follow(monkeypatch):
    class _FakeFaker:
        @staticmethod
        def random_element(options):
            return "YES"

    monkeypatch.setattr(base_agent_module.np.random, "rand", lambda: 0.0)
    monkeypatch.setattr(
        __import__("y_client.classes.fake_base_agent", fromlist=["Faker"]),
        "Faker",
        lambda: _FakeFaker(),
    )

    applied = []
    source = FakeAgent.__new__(FakeAgent)
    source.user_id = 7
    source.probability_of_secondary_follow = 1.0
    source.follow = lambda **kwargs: applied.append(kwargs) or "ok"

    result = source._FakeAgent__evaluate_follow("post", 14, "follow", 9)

    assert result == "follow"
    assert applied == [{"post_id": 14, "action": "follow", "tid": 9}]
