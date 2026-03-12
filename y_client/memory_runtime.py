from __future__ import annotations

import sys
from pathlib import Path


MEMORY_SRC = Path(__file__).resolve().parents[2] / "y_memory_subsystem" / "src"
if MEMORY_SRC.exists() and str(MEMORY_SRC) not in sys.path:
    sys.path.insert(0, str(MEMORY_SRC))

from yclient_memory import build_memory_engine  # type: ignore
from yclient_memory.config import MemoryConfig  # type: ignore


class YClientMemoryRuntime:
    def __init__(self, agent):
        self.agent = agent

    def llm_json(self, prompt_key, variables, config=None):
        return {}

    def llm_text(self, prompt_key, variables, config=None):
        return ""

    def get_author_id_and_username(self, post_id):
        return self.agent._memory_get_author_id_and_username(int(post_id))

    def get_thread_root_id(self, post_id):
        return self.agent._memory_get_thread_root_id(int(post_id))

    def get_recent_root_posts(self, round_id, limit=24, rounds_back=18):
        return self.agent._memory_get_recent_root_posts(
            tid=int(round_id),
            limit=int(limit),
            rounds_back=int(rounds_back),
        )

    def get_post_text(self, post_id):
        getter = getattr(self.agent, f"_{self.agent.__class__.__name__}__get_post", None)
        if getter is None:
            return ""
        try:
            return getter(int(post_id))
        except Exception:
            return ""

    def persona_snapshot(self):
        return {
            "user_id": getattr(self.agent, "user_id", None),
            "name": getattr(self.agent, "name", None),
            "language": getattr(self.agent, "language", None),
            "leaning": getattr(self.agent, "leaning", None),
        }

    def decision_log(self, payload):
        return None


def build_agent_memory_engine(agent):
    prompt_mode = str(getattr(agent, "memory_prompt_mode", "subtle_timeline") or "subtle_timeline")
    raw = {
        "memory_enabled": getattr(agent, "memory_enabled", False),
        "memory_backend": getattr(agent, "memory_backend", "hybrid_semantic"),
        "memory_prompt_mode": "subtle_forum" if prompt_mode == "subtle_timeline" else prompt_mode,
        "memory_vote_signal_only": getattr(agent, "memory_vote_signal_only", True),
        "memory_reply_context_max_chars": getattr(agent, "memory_reply_context_max_chars", 220),
        "memory_cross_thread_callback_min_score": getattr(
            agent, "memory_cross_thread_callback_min_score", 0.80
        ),
        "memory_high_affect_enabled": getattr(agent, "memory_high_affect_enabled", False),
        "memory_high_affect_rule_threshold": getattr(agent, "memory_high_affect_rule_threshold", 0.55),
        "memory_high_affect_uncertain_low": getattr(agent, "memory_high_affect_uncertain_low", 0.35),
        "memory_high_affect_uncertain_high": getattr(agent, "memory_high_affect_uncertain_high", 0.70),
        "memory_high_affect_search_k": getattr(agent, "memory_high_affect_search_k", 12),
        "memory_high_affect_max_items": getattr(agent, "memory_high_affect_max_items", 6),
        "memory_high_affect_max_chars": getattr(agent, "memory_high_affect_max_chars", 900),
        "memory_high_affect_llm_fallback": getattr(agent, "memory_high_affect_llm_fallback", False),
        "memory_nuance_enabled": getattr(agent, "memory_nuance_enabled", True),
        "memory_nuance_min_score": getattr(agent, "memory_nuance_min_score", 0.35),
        "memory_nuance_callback_probability": getattr(agent, "memory_nuance_callback_probability", 0.55),
        "memory_nuance_cues_max_chars": getattr(agent, "memory_nuance_cues_max_chars", 320),
    }
    config = MemoryConfig.from_mapping(raw)
    runtime = YClientMemoryRuntime(agent)
    engine = build_memory_engine(
        backend=str(raw["memory_backend"] or "hybrid_semantic"),
        config=config,
        runtime=runtime,
    )
    return runtime, engine
