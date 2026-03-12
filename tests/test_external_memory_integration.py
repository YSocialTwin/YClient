from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import y_client.classes.base_agent as base_agent_module
from y_client.classes.base_agent import Agent


def make_agent() -> Agent:
    agent = Agent.__new__(Agent)
    agent.name = "tester"
    agent.user_id = 11
    agent.base_url = "http://example.test/"
    agent.memory_enabled = True
    agent.memory_backend = "hybrid_semantic"
    agent.memory_prompt_mode = "subtle_timeline"
    agent.memory_vote_signal_only = True
    agent.memory_reply_context_max_chars = 220
    agent.memory_nuance_enabled = True
    agent.memory_nuance_min_score = 0.35
    agent.memory_nuance_callback_probability = 0.55
    agent.memory_nuance_cues_max_chars = 320
    agent.memory_cross_thread_callback_min_score = 0.8
    agent.memory_high_affect_enabled = False
    agent.memory_high_affect_rule_threshold = 0.55
    agent.memory_high_affect_uncertain_low = 0.35
    agent.memory_high_affect_uncertain_high = 0.70
    agent.memory_high_affect_search_k = 12
    agent.memory_high_affect_max_items = 6
    agent.memory_high_affect_max_chars = 900
    agent.memory_high_affect_llm_fallback = False
    agent.memory_run_id = "run-1"
    agent._external_memory_runtime = None
    agent._external_memory_engine = None
    agent._external_memory_disabled = False
    return agent


def test_memory_config_defaults_are_disabled():
    config = json.loads(Path("config_files/config.json").read_text())
    assert config["agents"]["memory_enabled"] is False
    assert config["agents"]["memory_prompt_mode"] == "subtle_timeline"


def test_memory_api_post_returns_empty_on_failure(monkeypatch):
    agent = make_agent()

    def raising_post(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(base_agent_module, "post", raising_post)
    assert agent._memory_api_post("/memory/search", {"x": 1}) == {}


def test_memory_disabled_skips_engine_creation():
    agent = make_agent()
    agent.memory_enabled = False
    assert agent._memory_get_external_engine() is None


def test_memory_build_reply_context_delegates_to_external_engine(monkeypatch):
    agent = make_agent()
    captured = {}

    class DummyEngine:
        def build_reply_context(self, request):
            captured["request"] = request
            diagnostics = SimpleNamespace(
                search_used=True,
                degraded_mode=False,
                embedding_degraded=False,
                no_ready_candidates=False,
                retrieved_item_count=2,
                top_score=0.91,
            )
            return SimpleNamespace(
                rendered_text="History with @alice: warm",
                diagnostics=diagnostics,
                continuity_text="warm history",
            )

    monkeypatch.setattr(agent, "_memory_get_external_engine", lambda: DummyEngine())

    text, meta = agent._memory_build_reply_context(
        query_text="hello there",
        other_user_id=22,
        thread_root_id=33,
        other_username="alice",
        round_id=5,
    )

    assert text == "History with @alice: warm"
    assert meta["search_used"] is True
    assert meta["retrieved_item_count"] == 2
    assert captured["request"].other_user_id == 22
    assert captured["request"].thread_root_id == 33
    assert captured["request"].other_username == "alice"


def test_memory_prompt_with_comment_context_appends_memory(monkeypatch):
    agent = make_agent()
    monkeypatch.setattr(agent, "_memory_get_author_id_and_username", lambda post_id: (44, "alice"))
    monkeypatch.setattr(agent, "_memory_get_thread_root_id", lambda post_id: 99)
    monkeypatch.setattr(
        agent,
        "_memory_build_reply_context",
        lambda **kwargs: ("History with @alice: supportive", {"usage": "reply"}),
    )
    monkeypatch.setattr(
        agent,
        "_memory_build_thread_browse_context",
        lambda **kwargs: ("thread gist: talking about music", {"usage": "thread_local"}),
    )

    prompt = agent._memory_prompt_with_comment_context(
        base_prompt="Base prompt",
        post_id=7,
        tid=3,
        conv_text="@alice - hi",
    )

    assert "Base prompt" in prompt
    assert "History with @alice: supportive" in prompt
    assert "thread gist: talking about music" in prompt


def test_memory_after_vote_records_vote_event(monkeypatch):
    agent = make_agent()
    recorded = {}

    class DummyEngine:
        def record_vote(self, event):
            recorded["event"] = event

    monkeypatch.setattr(agent, "_memory_get_external_engine", lambda: DummyEngine())
    agent._memory_after_vote(tid=9, post_id=101, vote_type="like")

    assert recorded["event"].round_id == 9
    assert recorded["event"].post_id == 101
    assert recorded["event"].vote_type == "like"


def test_memory_after_comment_records_comment_event(monkeypatch):
    agent = make_agent()
    recorded = {}

    class DummyEngine:
        def record_comment(self, event):
            recorded["event"] = event

    monkeypatch.setattr(agent, "_memory_get_external_engine", lambda: DummyEngine())
    agent._memory_after_comment(
        tid=4,
        target_post_id=88,
        thread_root_id=12,
        other_user_id=77,
        other_username="alice",
        other_text="original post",
        my_text="my reply",
        conv_text="@alice - original post",
    )

    assert recorded["event"].target_post_id == 88
    assert recorded["event"].thread_root_id == 12
    assert recorded["event"].other_user_id == 77
    assert recorded["event"].my_text == "my reply"


def test_memory_after_post_records_origin_kind(monkeypatch):
    agent = make_agent()
    recorded = {}

    class DummyEngine:
        def record_post(self, event):
            recorded["event"] = event

    monkeypatch.setattr(agent, "_memory_get_external_engine", lambda: DummyEngine())
    agent._memory_after_post(tid=6, post_text="shared article", origin_kind="share_link")

    assert recorded["event"].round_id == 6
    assert recorded["event"].text == "shared article"
    assert recorded["event"].origin_kind == "share_link"
