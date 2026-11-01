"""Client side of the federation: off by default, hides inactive agents, the agent's cross-post choice."""

import random
from types import SimpleNamespace

from y_client import federation


def _agents(n=6):
    return [SimpleNamespace(user_id=i) for i in range(1, n + 1)]


def _on(monkeypatch, inactive, **section):
    federation.install({"servers": {"api": "http://srv/"}, "federation": dict(enabled=True, seed=3, **section)})
    monkeypatch.setattr(federation.requests, "get", lambda url, timeout=0: SimpleNamespace(json=lambda: {"inactive": inactive}))


def test_off_by_default_changes_nothing_and_draws_nothing():
    federation.install({"servers": {"api": "http://srv/"}})
    agents = _agents()
    state = random.getstate()
    assert federation.filter_pool(agents) is agents and federation.post_fields() == {} and federation.inactive_ids() == set()
    assert random.getstate() == state and not federation.enabled()
    federation.install({"federation": {"enabled": False, "crosspost_propensity": 1.0}})
    assert federation.post_fields() == {}


def test_inactive_agents_are_left_out_of_the_pool(monkeypatch):
    _on(monkeypatch, [2, 5])
    agents = _agents()
    assert [a.user_id for a in federation.filter_pool(agents)] == [1, 3, 4, 6]
    _on(monkeypatch, [])
    assert federation.filter_pool(agents) is agents  # nobody hidden: the same list, same sampling as standalone
    federation.install({})


def test_the_last_known_list_is_kept_when_the_server_is_unreachable(monkeypatch):
    _on(monkeypatch, [4])
    assert federation.inactive_ids() == {4}

    def boom(url, timeout=0):
        raise OSError("down")

    monkeypatch.setattr(federation.requests, "get", boom)
    assert federation.inactive_ids() == {4}
    federation.install({})


def test_crosspost_choice_is_a_seeded_draw_with_its_own_generator(monkeypatch):
    _on(monkeypatch, [], crosspost_propensity=0.5)
    state = random.getstate()
    first = [bool(federation.post_fields()) for _ in range(40)]
    assert random.getstate() == state  # the global generator is untouched
    _on(monkeypatch, [], crosspost_propensity=0.5)
    assert first == [bool(federation.post_fields()) for _ in range(40)] and 0 < sum(first) < 40
    _on(monkeypatch, [], crosspost_propensity=0.0)
    assert federation.post_fields() == {}
    _on(monkeypatch, [], crosspost_propensity=1.0)
    assert federation.post_fields() == {"crosspost": True}
    federation.install({})


def test_attention_multiplier_scales_the_actions_with_its_own_generator(monkeypatch):
    def get(url, timeout=0):
        if url.endswith("/federation/attention"):
            return SimpleNamespace(json=lambda: {"multipliers": {"1": 2.0, "2": 0.5, "3": 1.0}})
        return SimpleNamespace(json=lambda: {"inactive": []})

    federation.install({"servers": {"api": "http://srv/"}, "federation": {"enabled": True, "seed": 3}})
    monkeypatch.setattr(federation.requests, "get", get)
    state = random.getstate()
    assert federation.scale_actions(3, 1) == 3  # nothing known yet: unchanged
    federation.filter_pool(_agents())  # reads the multipliers with the pool
    assert federation.scale_actions(3, 1) == 6 and federation.scale_actions(3, 3) == 3 and federation.scale_actions(3, 9) == 3
    half = [federation.scale_actions(1, 2) for _ in range(200)]
    assert set(half) == {0, 1} and 70 < sum(half) < 130  # 1 * 0.5 rounded at random, can be 0
    assert min(federation.scale_actions(1, 1) for _ in range(20)) == 2 and random.getstate() == state
    federation.install({"servers": {"api": "http://srv/"}, "federation": {"enabled": True, "seed": 3}})
    monkeypatch.setattr(federation.requests, "get", get)
    federation.filter_pool(_agents())
    assert [federation.scale_actions(1, 2) for _ in range(200)] == half  # reproducible
    federation.install({})
    assert federation.scale_actions(5, 1) == 5  # federation off: identity


def test_adoption_is_off_unless_configured_and_adopts_each_account_once(monkeypatch):
    class Client:
        def __init__(self):
            self.adopted = []

        def adopt_federated_account(self, account):
            self.adopted.append(account["username"])
            return SimpleNamespace(user_id=account["user_id"]) if account["username"] != "broken" else None

    accounts = [{"user_id": 7, "username": "newcomer"}, {"user_id": 8, "username": "broken"}]
    posted = []
    monkeypatch.setattr(federation.requests, "get", lambda url, timeout=0: SimpleNamespace(json=lambda: {"accounts": accounts}))
    monkeypatch.setattr(federation.requests, "post", lambda url, json=None, timeout=0: posted.append((url, json)))
    federation.install({"servers": {"api": "http://srv/"}, "federation": {"enabled": True}})
    c = Client()
    assert federation.adopt_provisioned(c) == 0 and c.adopted == [] and posted == []  # no `adopt`: nothing asked
    federation.install({"servers": {"api": "http://srv/"}, "federation": {"enabled": True, "adopt": True}})
    assert federation.adopt_provisioned(c) == 1 and c.adopted == ["newcomer", "broken"]
    assert posted == [("http://srv/federation/provisioned/adopted", {"user_ids": [7]})]  # the broken one is offered again
    federation.install({})
    assert federation.adopt_provisioned(c) == 0


def test_adopted_account_gets_the_agent_class_of_the_experiment(monkeypatch):
    """INV-19: a rule-based experiment (no model) adopts a provisioned account as a FakeAgent, like generate_user would."""
    from y_client.classes import base_agent as base_module
    from y_client.classes import fake_base_agent as fake_module
    from y_client.clients.client_base import YClientBase

    class _Built:
        def __init__(self, **kw):
            self.kind, self.name, self.user_id = type(self).__name__, kw["name"], 9

        def set_prompts(self, prompts):
            pass

        def set_rec_sys(self, *a):
            pass

    class Real(_Built):
        pass

    class Fake(_Built):
        pass

    import y_client.classes as classes

    monkeypatch.setattr(classes, "Agent", Real, raising=False)
    monkeypatch.setattr(classes, "FakeAgent", Fake, raising=False)
    monkeypatch.setattr(base_module, "Agent", Real)
    monkeypatch.setattr(fake_module, "FakeAgent", Fake)
    monkeypatch.setattr("y_client.clients.client_base.Agent", Real, raising=False)
    for llm_agents, expected in (([None], "Fake"), (["llama3"], "Real")):
        client = YClientBase.__new__(YClientBase)
        client.config = {"agents": {"llm_agents": llm_agents}}
        client.agents = base_module.Agents()
        client.prompts, client.content_recsys, client.follow_recsys, client.agents_owner = {}, None, None, "admin"
        agent = client.adopt_federated_account({"user_id": 9, "username": "newcomer", "interests": []})
        assert agent is not None and agent.kind == expected
