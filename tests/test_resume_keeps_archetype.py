"""Resuming a run: the agents rebuilt from the server keep the archetype of the agents file.

The server never stores the archetype (``user_mgmt.archetype`` is NULL), so ``/get_user`` returns ``None``. The load
branch used to copy that value over the one read from the agents file: after a resume every agent had archetype
``None`` and the archetype-stratified sampler of YWeb found no candidate for validator/broadcaster/explorer, so the
microblogging client advanced the slots without any agent acting (World Simulation 1, experiment 7).
"""

import json

import pytest

from y_client.classes import base_agent
from y_client.classes.base_agent import Agent

USER = {
    "id": 7, "user_type": "qwen3", "age": 30, "is_page": 0, "leaning": "neutral", "password": "x",
    "oe": "a", "co": "a", "ex": "a", "ag": "a", "ne": "a", "rec_sys": "ContentRecSys", "frec_sys": "FollowRecSys",
    "language": "English", "owner": "Admin", "education_level": "hs", "round_actions": 3, "joined_on": 1,
    "gender": "male", "toxicity": "low", "nationality": "US", "archetype": None,
}

CONFIG = {
    "servers": {"api": "http://srv.test/", "llm": "http://llm.test/v1", "llm_api_key": "NULL", "llm_v": "http://llm.test/v1",
                "llm_v_api_key": "NULL", "llm_v_temperature": 0.5, "llm_v_max_tokens": 10, "llm_max_tokens": -1,
                "llm_temperature": 1.0},
    "agents": {"llm_v_agent": "m", "attention_window": 10, "n_interests": {"min": 1, "max": 2}, "probability_of_secondary_follow": 0,
               "probability_of_follow_back": 0, "llm_agents": []},
    "simulation": {"actions_likelihood": {"post": 1.0}, "opinion_dynamics": {"enabled": False}},
    "posts": {"emotions": {}},
}


class _Response:
    def __init__(self, payload):
        self._content = json.dumps(payload).encode()
        self.status_code = 200

    def json(self):
        return json.loads(self._content)


def _fake_http(user):
    def route(url, headers=None, data=None, **kw):
        if url.endswith("/get_user"):
            return _Response(user)
        if url.endswith("/current_time"):
            return _Response({"id": 5, "day": 0, "round": 5})
        if url.endswith("/get_user_interests"):
            return _Response([{"topic": "Test1", "id": 1}])
        return _Response({"status": 200})

    return route


@pytest.mark.parametrize("server_value, expected", [(None, "validator"), ("", "validator"), ("explorer", "explorer")])
def test_resumed_agent_keeps_the_archetype_of_the_agents_file(monkeypatch, server_value, expected):
    user = dict(USER, archetype=server_value)
    monkeypatch.setattr(base_agent, "post", _fake_http(user))
    monkeypatch.setattr(base_agent, "get", _fake_http(user))
    monkeypatch.setattr(base_agent, "_fetch_current_round_id", lambda config: 1)
    import y_client.recsys as recsys

    agent = Agent(name="a", email="a@x", config=CONFIG, load=True, web=True, archetype="validator",
                  recsys=recsys.ContentRecSys(), frecsys=recsys.FollowRecSys(),
                  activity_profile="Always On", round_actions=3)
    assert agent.archetype == expected  # the server value wins only when it has one
    assert agent.user_id == 7
