"""P15: several members of one platform type. The client keys the prompt, the rule text and the length limit by the `platform` of
a destination (learned from the destinations answer), not by its member name (`microblogging-4`, `forum-9`)."""

import random
from types import SimpleNamespace

import pytest

from y_client import federation

MEMBERS = [{"member": "forum-9", "platform": "forum", "name": "Agora"},
           {"member": "microblogging-4", "platform": "microblogging", "name": "Beta"}]
LONG = "word " * 90  # 450 characters


def _on(monkeypatch, answer, propensity=1.0, name=None):
    section = dict(enabled=True, seed=3, member="microblogging-1", crosspost_mode="agent_action", crosspost_propensity=propensity)
    if name:
        section["name"] = name
    federation.install({"servers": {"api": "http://srv/"}, "federation": section})
    monkeypatch.setattr(federation.requests, "get", lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: answer))


@pytest.fixture(autouse=True)
def _reset():
    yield
    federation.install({})


def test_the_platform_of_a_member_comes_from_the_destinations_answer(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum-9", "microblogging-4"], "members": MEMBERS})
    assert federation.destinations(1) == ["forum-9", "microblogging-4"]
    assert federation.platform_of("microblogging-4") == "microblogging" and federation.platform_of("forum-9") == "forum"
    assert federation.adapt_prompt_key("microblogging-4") == "crosspost_adapt_microblogging"
    assert federation.adapt_prompt_key("forum-9") == "crosspost_adapt_forum"
    assert federation.adapt_prompt_key("mystery-3") is None  # not a known platform


def test_rule_text_and_parse_reply_use_the_limit_and_the_shape_of_the_platform(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum-9", "microblogging-4"], "members": MEMBERS})
    federation.destinations(1)
    assert len(federation.rule_text("microblogging-4", LONG)) <= 280
    forum = federation.rule_text("forum-9", "Nice day. Go out.")
    assert forum.startswith("Nice day.\n")  # a forum thread: title line then body
    assert len(federation.rule_text("forum-9", LONG)) > 280  # the forum limit is 2000
    assert federation.parse_reply("forum-9", "Title: A title\nBody: some words") == "A title\nsome words"
    assert len(federation.parse_reply("microblogging-4", LONG)) <= 280


def test_agent_action_posts_to_two_members_of_one_platform_type(monkeypatch):
    members = MEMBERS + [{"member": "microblogging-7", "platform": "microblogging", "name": "Gamma"}]
    _on(monkeypatch, {"destinations": [m["member"] for m in members], "members": members})
    fields = federation.post_fields(1, LONG, lambda dest, text: None)
    assert [t["member"] for t in fields["crosspost_to"]] == ["forum-9", "microblogging-4", "microblogging-7"]  # one draw each, sorted
    by = {t["member"]: t["text"] for t in fields["crosspost_to"]}
    assert len(by["microblogging-4"]) <= 280 and len(by["microblogging-7"]) <= 280 and len(by["forum-9"]) > 280


def test_one_draw_per_member_not_per_platform(monkeypatch):
    members = MEMBERS + [{"member": "microblogging-7", "platform": "microblogging", "name": "Gamma"}]
    _on(monkeypatch, {"destinations": [m["member"] for m in members], "members": members}, propensity=0.5)
    expected = random.Random(3)
    want = [d for d in ["forum-9", "microblogging-4", "microblogging-7"] if expected.random() < 0.5]
    got = federation.post_fields(1, "some text")
    assert [t["member"] for t in got.get("crosspost_to", [])] == want


def test_the_model_prompt_lines_name_the_member_its_experiment_and_its_platform(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum-9", "microblogging-4"], "members": MEMBERS})
    dests = federation.destinations(1)
    assert federation.destination_lines(dests).splitlines() == ["- forum-9 (Agora, forum, 2000)", "- microblogging-4 (Beta, microblogging, 280)"]


def test_a_member_named_after_its_platform_keeps_the_old_prompt_line(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum", "microblogging"],
                      "members": [{"member": "forum", "platform": "forum", "name": "forum"},
                                  {"member": "microblogging", "platform": "microblogging", "name": "microblogging"}]})
    dests = federation.destinations(1)
    assert federation.destination_lines(dests) == "- forum (2000)\n- microblogging (280)"
    assert federation.adapt_prompt_key("forum") == "crosspost_adapt_forum"


def test_an_older_server_answers_only_member_names(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum", "microblogging"]})
    assert federation.destinations(1) == ["forum", "microblogging"]
    assert federation.platform_of("forum") == "forum" and federation.adapt_prompt_key("microblogging") == "crosspost_adapt_microblogging"
    fields = federation.post_fields(1, "hello world", None)
    assert [t["member"] for t in fields["crosspost_to"]] == ["forum", "microblogging"]


def test_the_source_platform_is_the_experiment_name_when_the_member_section_has_one(monkeypatch):
    _on(monkeypatch, {"destinations": []}, name="Alpha")
    assert federation.source_platform() == "Alpha"
    _on(monkeypatch, {"destinations": []})
    assert federation.source_platform() == "microblogging-1"


def test_install_forgets_what_was_learned(monkeypatch):
    _on(monkeypatch, {"destinations": ["forum-9"], "members": MEMBERS})
    federation.destinations(1)
    federation.install({})
    assert federation.platform_of("forum-9") == "forum-9"
