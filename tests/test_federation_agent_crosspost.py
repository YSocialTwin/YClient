"""F6.2: cross-post as an agent action on the client: the choice, the rule text, the parsing of recorded model replies."""

import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from y_client import federation, prompt_store


def _on(monkeypatch, dests, mode="agent_action", propensity=1.0, **kw):
    federation.install({"servers": {"api": "http://srv/"},
                        "federation": dict(enabled=True, seed=3, member="microblogging", crosspost_mode=mode,
                                           crosspost_propensity=propensity, **kw)})
    monkeypatch.setattr(federation.requests, "get", lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: {"destinations": dests}))


def test_off_or_other_mode_changes_nothing(monkeypatch):
    federation.install({})
    state = random.getstate()
    assert federation.post_fields(1, "text", lambda d, t: "x") == {} and random.getstate() == state
    _on(monkeypatch, ["forum"], mode="coordinator_rule")
    assert not federation.agent_action()
    assert federation.post_fields(1, "text") == {"crosspost": True}  # the old behaviour, unchanged
    federation.install({})


def test_agent_action_posts_to_the_chosen_destinations_with_a_text_for_each(monkeypatch):
    _on(monkeypatch, ["forum", "dating"])
    fields = federation.post_fields(1, "I love the new park downtown. Everyone should go.", None)
    assert fields["crosspost"] is True
    assert [t["member"] for t in fields["crosspost_to"]] == ["dating", "forum"]
    assert fields["crosspost_to"][1]["text"].startswith("I love the new park downtown.\nI love the new park")
    assert fields["crosspost_to"][0]["text"] == "I love the new park downtown. Everyone should go."
    federation.install({})


def test_the_model_version_is_used_and_a_failure_falls_back_to_the_rule_text(monkeypatch):
    _on(monkeypatch, ["dating", "forum"])
    fields = federation.post_fields(1, "hello world", lambda dest, text: "from the model" if dest == "dating" else None)
    assert {t["member"]: t["text"] for t in fields["crosspost_to"]} == {"dating": "from the model", "forum": "hello world\nhello world"}
    federation.install({})


def test_one_draw_per_destination_from_the_own_generator(monkeypatch):
    _on(monkeypatch, ["forum", "dating", "photo_sharing"], propensity=0.5)
    state = random.getstate()
    runs = [[t["member"] for t in federation.post_fields(1, "t text")["crosspost_to"]] if federation.post_fields(1, "t text") else [] for _ in range(1)]
    assert random.getstate() == state  # the global generator is untouched
    _on(monkeypatch, ["forum", "dating", "photo_sharing"], propensity=0.5)
    expected = random.Random(3)
    want = [d for d in ["dating", "forum", "photo_sharing"] if expected.random() < 0.5]
    got = federation.post_fields(1, "t text").get("crosspost_to", [])
    assert [t["member"] for t in got] == want
    federation.install({})


def test_no_destination_or_zero_propensity_means_no_field(monkeypatch):
    _on(monkeypatch, [])
    assert federation.post_fields(1, "text") == {}
    _on(monkeypatch, ["forum"], propensity=0.0)
    assert federation.post_fields(1, "text") == {}
    federation.install({})


def test_an_unreachable_server_means_no_cross_post(monkeypatch):
    _on(monkeypatch, ["forum"])

    def boom(*a, **k):
        raise OSError("down")

    monkeypatch.setattr(federation.requests, "get", boom)
    assert federation.post_fields(1, "text") == {}
    federation.install({})


@pytest.mark.parametrize("dest,reply,expected", [
    ("microblogging", '"Great park! #city #sunny #extra"', "Great park! #city #sunny #extra"),
    ("microblogging", "<think>let me think</think>\nPost: nice day out", "nice day out"),
    ("microblogging", "x" * 400, "x" * 280),
    ("microblogging", "  ", None),
    ("forum", "Title: The new park\nIt opened last week. Has anyone been?\nTell me what you think.", "The new park\nIt opened last week. Has anyone been? Tell me what you think."),
    ("forum", "# A park\n", "A park\nA park"),
    ("forum", "", None),
    ("photo_sharing", "```\nGolden hour at the park ✨\n```", "Golden hour at the park ✨"),
    ("instant_messaging", "«hey, did you see the park?»", "hey, did you see the park?"),
    ("dating", "Didascalia: Amo i parchi e le passeggiate lente.", "Amo i parchi e le passeggiate lente."),
    ("dating", "y" * 250, "y" * 200),
])
def test_recorded_model_replies_are_parsed(dest, reply, expected):
    assert federation.parse_reply(dest, reply) == expected


def test_the_five_prompts_exist_in_both_languages_and_render():
    root = Path(prompt_store.__file__).parent
    for suffix in ("", ".it"):
        pack = json.loads((root / f"prompts_internal{suffix}.json").read_text(encoding="utf-8"))
        for dest in federation.LIMITS:
            assert f"crosspost_adapt_{dest}" in pack
    for dest in federation.LIMITS:
        for lang in ("en", "it"):
            text = prompt_store.prompt(federation.adapt_prompt_key(dest), language=lang, source_platform="forum", text="SAMPLE")
            assert "SAMPLE" in text and "forum" in text and "{" not in text
    assert federation.adapt_prompt_key("unknown") is None
