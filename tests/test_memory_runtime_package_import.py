from __future__ import annotations

import builtins
import sys
import types
from types import SimpleNamespace

import y_client.memory_runtime as memory_runtime_module


def make_agent():
    return SimpleNamespace(
        name="tester",
        user_id=11,
        language="english",
        leaning="neutral",
        memory_enabled=True,
        memory_backend="hybrid_semantic",
        memory_prompt_mode="subtle_timeline",
        memory_vote_signal_only=True,
        memory_reply_context_max_chars=220,
        memory_cross_thread_callback_min_score=0.8,
        memory_high_affect_enabled=False,
        memory_high_affect_rule_threshold=0.55,
        memory_high_affect_uncertain_low=0.35,
        memory_high_affect_uncertain_high=0.70,
        memory_high_affect_search_k=12,
        memory_high_affect_max_items=6,
        memory_high_affect_max_chars=900,
        memory_high_affect_llm_fallback=False,
        memory_nuance_enabled=True,
        memory_nuance_min_score=0.35,
        memory_nuance_callback_probability=0.55,
        memory_nuance_cues_max_chars=320,
    )


def test_memory_runtime_loads_installed_package(monkeypatch):
    fake_package = types.ModuleType("yclient_memory")
    fake_config_module = types.ModuleType("yclient_memory.config")
    captured = {}

    def fake_build_memory_engine(**kwargs):
        captured.update(kwargs)
        return "engine"

    class FakeMemoryConfig:
        @classmethod
        def from_mapping(cls, mapping):
            return {"config": mapping}

    fake_package.build_memory_engine = fake_build_memory_engine
    fake_config_module.MemoryConfig = FakeMemoryConfig

    monkeypatch.setitem(sys.modules, "yclient_memory", fake_package)
    monkeypatch.setitem(sys.modules, "yclient_memory.config", fake_config_module)

    runtime, engine = memory_runtime_module.build_agent_memory_engine(make_agent())

    assert engine == "engine"
    assert runtime.agent.name == "tester"
    assert captured["backend"] == "hybrid_semantic"
    assert captured["config"]["config"]["memory_prompt_mode"] == "subtle_forum"


def test_memory_runtime_raises_clear_error_without_package(monkeypatch):
    monkeypatch.delitem(sys.modules, "yclient_memory", raising=False)
    monkeypatch.delitem(sys.modules, "yclient_memory.config", raising=False)

    original_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "yclient_memory" or name == "yclient_memory.config":
            raise ImportError("missing test package")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)

    try:
        memory_runtime_module.build_agent_memory_engine(make_agent())
    except RuntimeError as exc:
        assert "yclient-memory" in str(exc)
    else:
        raise AssertionError("Expected a RuntimeError when yclient-memory is unavailable")
