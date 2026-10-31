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
