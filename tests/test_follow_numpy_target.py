"""follow() must send targets picked with numpy (np.random.choice returns numpy.int64, not int)."""

import json

import numpy as np

from y_client.classes import base_agent as base_agent_module
from y_client.classes import fake_base_agent as fake_base_agent_module
from y_client.classes.base_agent import Agent
from y_client.classes.fake_base_agent import FakeAgent


def _agent(cls):
    agent = cls.__new__(cls)
    agent.user_id = 7
    agent.base_url = "http://example.test"
    agent.simulation_client = None
    return agent


def _capture_posts(monkeypatch, module):
    posted = []
    monkeypatch.setattr(module, "post", lambda url, headers=None, data=None: posted.append((url, json.loads(data))))
    return posted


def test_fake_agent_follow_sends_numpy_integer_target(monkeypatch):
    posted = _capture_posts(monkeypatch, fake_base_agent_module)
    target = np.random.choice([11], size=1)[0]  # numpy.int64, as in select_action

    _agent(FakeAgent).follow(tid=4, target=target, action="follow")

    assert posted == [("http://example.test/follow", {"user_id": 7, "target": 11, "action": "follow", "tid": 4})]


def test_llm_agent_follow_sends_numpy_integer_target(monkeypatch):
    posted = _capture_posts(monkeypatch, base_agent_module)
    target = np.random.choice([11], size=1)[0]

    _agent(Agent).follow(tid=4, target=target, action="follow")

    assert posted == [("http://example.test/follow", {"user_id": 7, "target": 11, "action": "follow", "tid": 4})]


def test_follow_without_target_sends_nothing(monkeypatch):
    posted_fake = _capture_posts(monkeypatch, fake_base_agent_module)
    posted_llm = _capture_posts(monkeypatch, base_agent_module)

    _agent(FakeAgent).follow(tid=4, target=None, action="follow")
    _agent(Agent).follow(tid=4, target=None, action="follow")

    assert posted_fake == [] and posted_llm == []
