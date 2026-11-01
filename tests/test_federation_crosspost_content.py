"""P13: crosspost.content is additive (OR): the agent is offered the cross-post of a share only when it can be eligible."""

from types import SimpleNamespace

import pytest

from y_client import federation


def _on(monkeypatch, **kw):
    federation.install({"servers": {"api": "http://srv/"},
                        "federation": dict(enabled=True, seed=3, member="microblogging", crosspost_mode="agent_action",
                                           crosspost_propensity=1.0, **kw)})
    monkeypatch.setattr(federation.requests, "get", lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: {"destinations": ["forum"]}))


@pytest.mark.parametrize("content", [None, ["all"], ["news"], ["images"], ["own_content", "news"], ["own_content", "images"], ["news", "images"]])
def test_a_share_is_offered_with_all_or_with_news_or_images(monkeypatch, content):
    _on(monkeypatch, **({} if content is None else {"crosspost_content": content}))
    assert federation.share_fields(1, "nice one")["crosspost_to"][0]["member"] == "forum"
    federation.install({})


@pytest.mark.parametrize("content", [["own_content"], ["own_posts"]])  # own_posts: legacy alias
def test_a_share_is_not_offered_with_only_own_content_and_a_post_still_is(monkeypatch, content):
    _on(monkeypatch, crosspost_content=content)
    rng_before = federation._state["rng"].getstate()
    assert federation.share_fields(1, "nice one") == {} and federation._state["rng"].getstate() == rng_before
    assert federation.post_fields(1, "my own words")["crosspost_to"][0]["member"] == "forum"
    federation.install({})
