"""P13: with crosspost.content including own_posts the agent is not offered the cross-post of a share."""

from types import SimpleNamespace

import pytest

from y_client import federation


def _on(monkeypatch, **kw):
    federation.install({"servers": {"api": "http://srv/"},
                        "federation": dict(enabled=True, seed=3, member="microblogging", crosspost_mode="agent_action",
                                           crosspost_propensity=1.0, **kw)})
    monkeypatch.setattr(federation.requests, "get", lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: {"destinations": ["forum"]}))


@pytest.mark.parametrize("content", [None, ["news"], ["images"]])
def test_a_share_is_offered_without_the_own_posts_restriction(monkeypatch, content):
    _on(monkeypatch, **({} if content is None else {"crosspost_content": content}))
    assert federation.share_fields(1, "nice one")["crosspost_to"][0]["member"] == "forum"
    federation.install({})


@pytest.mark.parametrize("content", [["own_posts"], ["own_posts", "news"]])
def test_a_share_is_not_offered_with_the_own_posts_restriction_and_a_post_still_is(monkeypatch, content):
    _on(monkeypatch, crosspost_content=content)
    rng_before = federation._state["rng"].getstate()
    assert federation.share_fields(1, "nice one") == {} and federation._state["rng"].getstate() == rng_before
    assert federation.post_fields(1, "my own words")["crosspost_to"][0]["member"] == "forum"
    federation.install({})
