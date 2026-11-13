"""P14: the agent's LLM decides whether (and where) to cross-post: crosspost.decision = llm, with a fake model."""

import json
import logging
import random
import time
from types import SimpleNamespace

import pytest

from y_client import federation, prompt_store


DECIDE_KEY = "crosspost_decide"  # not a literal at the call: the call-site ratchet checks the real call sites only
INTERACTION_KEY = "crosspost_decide_interaction"


def _on(monkeypatch, dests, mode="agent_action", propensity=1.0, decision="llm", **kw):
    section = dict(enabled=True, seed=3, member="microblogging", crosspost_mode=mode, crosspost_propensity=propensity, **kw)
    if decision is not None:
        section["crosspost_decision"] = decision
    federation.install({"servers": {"api": "http://srv/"}, "federation": section})
    monkeypatch.setattr(federation.requests, "get",
                        lambda url, params=None, timeout=0: SimpleNamespace(json=lambda: {"destinations": dests}))


class Fake:
    """A fake model: records its calls and answers with `reply` (a string, or a function of the call)."""

    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def __call__(self, trigger, text, dest_lines, context=None):
        self.calls.append((trigger, text, dest_lines, context))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply(trigger, text) if callable(self.reply) else self.reply


@pytest.fixture(autouse=True)
def _off():
    yield
    federation.install({})


def _rng_state():
    return federation._state["rng"].getstate()


# --- random mode is exactly what it was -------------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["coordinator_rule", "agent_action"])
def test_random_mode_is_bit_identical_and_never_calls_the_model(monkeypatch, mode):
    runs = []
    for decision in (None, "random"):
        _on(monkeypatch, ["forum", "dating"], mode=mode, propensity=0.5, decision=decision)
        ask = Fake("{}")
        runs.append([federation.post_fields(1, f"post number {i}", None, ask, i) for i in range(60)])
        assert ask.calls == []
        runs.append(_rng_state())
    assert runs[0] == runs[2] and runs[1] == runs[3]
    reference = random.Random(3)
    if mode == "coordinator_rule":
        assert [bool(f) for f in runs[0]] == [reference.random() < 0.5 for _ in range(60)]


def test_the_default_settings(monkeypatch):
    _on(monkeypatch, ["forum"], decision=None)
    assert federation._state["decision"] == "random" and federation._state["triggers"] == ("publish", "interaction")
    assert federation._state["max_per_day"] == 5 and not federation.decision_for("publish")


def test_unknown_decision_means_random_and_triggers_are_filtered(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="y_client.federation"):
        _on(monkeypatch, ["forum"], decision="oracle")
    assert federation._state["decision"] == "random" and "oracle" in caplog.text
    _on(monkeypatch, ["forum"], crosspost_decision_triggers=["interaction", "bogus"], crosspost_decision_max_per_day=2)
    assert federation._state["triggers"] == ("interaction",) and federation._state["max_per_day"] == 2
    assert federation.decision_for("interaction") and not federation.decision_for("publish")
    _on(monkeypatch, ["forum"], crosspost_decision_max_per_day="many")
    assert federation._state["max_per_day"] == federation.DEFAULT_MAX_PER_DAY


# --- agent_action: the model chooses where and with which words ---------------------------------------------------------
def test_llm_chooses_destinations_and_texts_without_touching_the_generator(monkeypatch):
    _on(monkeypatch, ["dating", "forum", "photo_sharing"], propensity=0.0)
    before, global_state = _rng_state(), random.getstate()
    ask = Fake(json.dumps({"crosspost": True, "destinations": ["forum", "photo_sharing"], "text": {"forum": "Title\nBody text"}}))
    fields = federation.post_fields(7, "A long walk in the park today.", lambda d, t: "adapted " + d, ask, 100)
    assert fields["crosspost"] is True
    assert [(t["member"], t["text"]) for t in fields["crosspost_to"]] == [("forum", "Title\nBody text"), ("photo_sharing", "adapted photo_sharing")]
    assert len(ask.calls) == 1 and ask.calls[0][0] == "publish"
    assert "- dating (200)" in ask.calls[0][2] and "- forum (2000)" in ask.calls[0][2]
    assert _rng_state() == before and random.getstate() == global_state  # even with propensity 0 the model decides


def test_text_without_model_text_nor_adapter_uses_the_rule_text(monkeypatch):
    _on(monkeypatch, ["forum"])
    fields = federation.post_fields(7, "hello world", None, Fake('{"crosspost": true, "destinations": ["forum"]}'), 1)
    assert fields["crosspost_to"] == [{"member": "forum", "text": "hello world\nhello world"}]


def test_the_model_says_no(monkeypatch):
    _on(monkeypatch, ["forum"])
    before = _rng_state()
    assert federation.post_fields(7, "hello world", None, Fake('{"crosspost": false, "destinations": []}'), 1) == {}
    assert _rng_state() == before


def test_unknown_destinations_are_ignored(monkeypatch):
    _on(monkeypatch, ["forum", "dating"])
    ask = Fake('{"crosspost": true, "destinations": ["myspace", "Forum", "forum"], "text": {"myspace": "no"}}')
    fields = federation.post_fields(7, "hello world", None, ask, 1)
    assert [t["member"] for t in fields["crosspost_to"]] == ["forum"]
    none = Fake('{"crosspost": true, "destinations": ["myspace"]}')
    assert federation.post_fields(7, "hello world", None, none, 2) == {}  # nothing valid: no cross-post, no draw


# --- coordinator_rule: the model only marks the content -----------------------------------------------------------------
def test_coordinator_rule_the_model_only_marks(monkeypatch):
    _on(monkeypatch, ["forum", "dating"], mode="coordinator_rule", propensity=0.0)
    before = _rng_state()
    yes = Fake('{"crosspost": true, "destinations": ["forum"], "text": {"forum": "x"}}')
    assert federation.post_fields(7, "hello world", None, yes, 1) == {"crosspost": True}
    assert federation.post_fields(7, "hello world", None, Fake('{"crosspost": false}'), 2) == {}
    assert _rng_state() == before


def test_coordinator_rule_never_offers_a_share(monkeypatch):
    _on(monkeypatch, ["forum"], mode="coordinator_rule")
    ask = Fake('{"crosspost": true, "destinations": ["forum"]}')
    assert federation.share_fields(7, "nice", None, ask, 1, {"action": "share", "content": "orig"}) == {} and ask.calls == []


# --- failures fall back to the Bernoulli draw ---------------------------------------------------------------------------
@pytest.mark.parametrize("reply", ["no json here", '{"crosspost": "maybe"}', '{"destinations": ["forum"]}', "", None, "{'crosspost': true}"])
def test_invalid_replies_fall_back_to_the_draw(monkeypatch, caplog, reply):
    _on(monkeypatch, ["forum"], mode="coordinator_rule", propensity=1.0)
    with caplog.at_level(logging.INFO, logger="y_client.federation"):
        assert federation.post_fields(7, "hello world", None, Fake(reply), 1) == {"crosspost": True}
    assert "source=fallback" in caplog.text and "reason=invalid" in caplog.text
    expected = random.Random(3)
    expected.random()
    assert _rng_state() == expected.getstate()  # the fallback consumed exactly one draw


def test_a_model_error_falls_back_and_is_logged(monkeypatch, caplog):
    _on(monkeypatch, ["forum"], propensity=1.0)
    with caplog.at_level(logging.INFO, logger="y_client.federation"):
        fields = federation.post_fields(7, "hello world", None, Fake(OSError("down")), 1)
    assert fields["crosspost_to"][0]["member"] == "forum"
    assert "source=fallback" in caplog.text and "reason=error:OSError" in caplog.text and "agent=7" in caplog.text


def test_a_slow_model_times_out_and_the_draw_is_used(monkeypatch):
    monkeypatch.setattr(federation, "DECISION_TIMEOUT", 0.05)
    _on(monkeypatch, ["forum"], mode="coordinator_rule", propensity=0.0)
    started = time.monotonic()
    assert federation.post_fields(7, "hello world", None, Fake(lambda t, x: time.sleep(1) or "{}"), 1) == {}
    assert time.monotonic() - started < 0.8


def test_fallback_with_zero_propensity_is_no_cross_post(monkeypatch):
    _on(monkeypatch, ["forum"], propensity=0.0)
    assert federation.post_fields(7, "hello world", None, Fake("garbage"), 1) == {}


# --- cost control -------------------------------------------------------------------------------------------------------
def test_cap_per_agent_per_day_then_the_draw(monkeypatch, caplog):
    _on(monkeypatch, ["forum"], mode="coordinator_rule", propensity=1.0, crosspost_decision_max_per_day=2)
    ask = Fake('{"crosspost": false}')
    out = [federation.post_fields(7, "hello world", None, ask, r) for r in (48, 50, 52)]
    assert out == [{}, {}, {"crosspost": True}] and len(ask.calls) == 2  # third: cap reached, Bernoulli
    federation.post_fields(8, "hello world", None, ask, 53)  # another agent has its own budget
    assert len(ask.calls) == 3
    federation.post_fields(7, "hello world", None, ask, 72)  # the next day
    assert len(ask.calls) == 4


def test_zero_cap_means_no_limit(monkeypatch):
    _on(monkeypatch, ["forum"], mode="coordinator_rule", crosspost_decision_max_per_day=0)
    ask = Fake('{"crosspost": false}')
    for r in range(20):
        federation.post_fields(7, "hello world", None, ask, r)
    assert len(ask.calls) == 20


def test_rule_based_agent_keeps_the_draw(monkeypatch):
    _on(monkeypatch, ["forum"], mode="coordinator_rule", propensity=0.5)
    got = [federation.post_fields(7, "hello world", None, None, r) for r in range(30)]
    reference = random.Random(3)
    assert got == [{"crosspost": True} if reference.random() < 0.5 else {} for _ in range(30)]


def test_no_destination_no_call_and_no_draw(monkeypatch):
    _on(monkeypatch, [])
    ask, before = Fake('{"crosspost": true}'), _rng_state()
    assert federation.post_fields(7, "hello world", None, ask, 1) == {} and ask.calls == [] and _rng_state() == before


def test_content_not_eligible_is_not_asked(monkeypatch):
    _on(monkeypatch, ["forum"], crosspost_content=["news"])
    ask, before = Fake('{"crosspost": true, "destinations": ["forum"]}'), _rng_state()
    assert federation.post_fields(7, "just my thoughts", None, ask, 1) == {} and ask.calls == [] and _rng_state() == before
    assert federation.post_fields(7, "read https://example.org/a", None, ask, 2)["crosspost"] is True and len(ask.calls) == 1
    _on(monkeypatch, ["forum"], crosspost_content=["own_posts"])  # legacy alias: own content is eligible
    assert federation.post_fields(7, "just my thoughts", None, ask, 3)["crosspost"] is True


def test_share_blocked_is_not_asked(monkeypatch):
    _on(monkeypatch, ["forum"], crosspost_content=["own_content"])
    ask = Fake('{"crosspost": true, "destinations": ["forum"]}')
    assert federation.share_fields(7, "nice", None, ask, 1, {"action": "share", "content": "orig"}) == {} and ask.calls == []


# --- triggers -----------------------------------------------------------------------------------------------------------
def test_interaction_trigger_on_a_share(monkeypatch):
    _on(monkeypatch, ["forum", "dating"], propensity=0.0)
    ask = Fake('{"crosspost": true, "destinations": ["dating"], "text": {"dating": "I loved this one"}}')
    fields = federation.share_fields(7, "my words", None, ask, 5, {"action": "share", "content": "their post"})
    assert fields == {"crosspost": True, "crosspost_to": [{"member": "dating", "text": "I loved this one"}]}
    assert ask.calls[0][0] == "interaction" and ask.calls[0][3] == {"action": "share", "content": "their post"}


def test_only_the_selected_triggers_call_the_model(monkeypatch):
    _on(monkeypatch, ["forum"], propensity=1.0, crosspost_decision_triggers=["interaction"])
    ask = Fake('{"crosspost": false}')
    assert federation.post_fields(7, "hello world", None, ask, 1)["crosspost"] is True and ask.calls == []  # publish: the draw
    assert federation.share_fields(7, "nice", None, ask, 2, {"action": "share"}) == {} and len(ask.calls) == 1
    _on(monkeypatch, ["forum"], propensity=1.0, crosspost_decision_triggers=["publish"])
    ask = Fake('{"crosspost": false}')
    assert federation.share_fields(7, "nice", None, ask, 2)["crosspost"] is True and ask.calls == []  # share: the draw
    assert federation.post_fields(7, "hello world", None, ask, 1) == {} and len(ask.calls) == 1


# --- record -------------------------------------------------------------------------------------------------------------
def test_each_decision_is_logged_and_counted(monkeypatch, caplog):
    _on(monkeypatch, ["forum"])
    base = federation.decision_stats()
    with caplog.at_level(logging.INFO, logger="y_client.federation"):
        federation.post_fields(7, "hello world", None, Fake('{"crosspost": true, "destinations": ["forum"]}'), 1)
    assert "federation_decision agent=7 trigger=publish source=llm crosspost=1 destinations=forum" in caplog.text
    stats = federation.decision_stats()
    assert stats["llm"] == base["llm"] + 1 and stats["crossposts_llm"] == base["crossposts_llm"] + 1


# --- parser -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("reply,expected", [
    ('{"crosspost": true, "destinations": ["forum"]}', {"crosspost": True, "destinations": ["forum"], "text": {}}),
    ('Sure!\n```json\n{"crosspost": false, "destinations": []}\n```', {"crosspost": False, "destinations": [], "text": {}}),
    ('<think>hmm {"crosspost": false}</think>{"crosspost": "yes", "destinations": ["dating"], "text": {"dating": "\\"hi there\\""}}',
     {"crosspost": True, "destinations": ["dating"], "text": {"dating": "hi there"}}),
    ('{"note": 1} then {"crosspost": true, "destinations": "forum"}', {"crosspost": True, "destinations": [], "text": {}}),
    ('{"crosspost": true, "destinations": ["forum"], "text": {"forum": "x" * 3000}}'.replace('"x" * 3000', '"' + "y" * 3000 + '"'),
     {"crosspost": True, "destinations": ["forum"], "text": {"forum": ("y" * 2000 + "\n" + "y" * 2000)[:2000]}}),
    ('{"crosspost": 1}', None), ("[]", None), ("{broken", None),
])
def test_parse_decision(reply, expected):
    result = federation.parse_decision(reply, ["dating", "forum"])
    if expected is not None and "forum" in expected["text"]:
        assert result["text"]["forum"].startswith("y" * 50) and len(result["text"]["forum"]) <= 2000
        expected = dict(expected, text=result["text"])
    assert result == expected


# --- prompts ------------------------------------------------------------------------------------------------------------
def test_the_decide_prompts_exist_in_both_languages_and_render():
    for lang in ("en", "it"):
        text = prompt_store.prompt(DECIDE_KEY, language=lang, name="Ann", profile="34, teacher", text="SAMPLE",
                                   trigger=prompt_store.get("crosspost_decide_publish", lang), destinations="- forum (2000)")
        assert "SAMPLE" in text and "Ann" in text and "- forum (2000)" in text and '"crosspost"' in text and "{profile}" not in text
        for action in ("share", "comment", "reply", "reaction"):
            assert prompt_store.get("crosspost_decide_action_" + action, lang)
        assert "{action}" not in prompt_store.prompt(INTERACTION_KEY, language=lang, action="x") and "x" in prompt_store.prompt(INTERACTION_KEY, language=lang, action="x")
    assert prompt_store.get("crosspost_decide", "it") != prompt_store.get("crosspost_decide", "en")


# --- the agent's side: prompt, model call, rule-based agent ---------------------------------------------------------------
def _agent(module, model="llama3"):
    agent = object.__new__(module.Agent)
    agent.name, agent.age, agent.gender, agent.profession, agent.interests = "Ann", 34, "female", "teacher", ["parks", "music"]
    agent.llm_config = {"config_list": [{"model": model}]}
    agent.prompts = {"handler_instructions": "sys", "handler_instructions_simple": "sys"}
    return agent


def test_the_agent_asks_its_model_once_and_the_answer_decides(monkeypatch):
    import y_client.classes.base_agent as module

    seen = []

    class Stub:
        def __init__(self, **kw):
            seen.append(kw)

        def _generate_reply(self, prompt):
            seen.append(prompt)
            return '{"crosspost": true, "destinations": ["forum"]}'

    monkeypatch.setattr(module, "AssistantAgent", Stub)
    agent = _agent(module)
    _on(monkeypatch, ["forum", "dating"])
    fields = federation.post_fields(7, "A day at the park", agent._crosspost_adapt, agent._crosspost_decider(), 30)
    assert fields["crosspost"] is True and [t["member"] for t in fields["crosspost_to"]] == ["forum"]
    decide_prompts = [p for p in seen if isinstance(p, str) and '"crosspost"' in p]
    assert len(decide_prompts) == 1  # one decision call; the adaptation call (another prompt) is a separate one
    assert "Ann" in decide_prompts[0] and "34, female, teacher; parks, music" in decide_prompts[0]
    assert "A day at the park" in decide_prompts[0] and "- dating (200)" in decide_prompts[0]
    shared = agent._crosspost_decide("interaction", "my words", "- forum (2000)", {"action": "share", "content": "THEIR POST"})
    assert shared and "THEIR POST" in seen[-1] and "my words" not in seen[-1] and "you shared it" in seen[-1]


def test_an_agent_without_a_model_keeps_the_draw(monkeypatch):
    import y_client.classes.base_agent as module

    assert _agent(module, model="none")._crosspost_decider() is None
    assert _agent(module)._crosspost_decider() is not None
