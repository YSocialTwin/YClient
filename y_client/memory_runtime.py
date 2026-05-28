from __future__ import annotations

def _load_memory_package():
    try:
        from yclient_memory import build_memory_engine  # type: ignore
        from yclient_memory.config import MemoryConfig  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The external memory integration requires the pip package "
            "'yclient-memory'. Install it before enabling agent memory."
        ) from exc
    return build_memory_engine, MemoryConfig


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
    build_memory_engine, MemoryConfig = _load_memory_package()
    prompt_mode = str(getattr(agent, "memory_prompt_mode", "subtle_timeline") or "subtle_timeline")
    raw = {
        "memory_enabled": getattr(agent, "memory_enabled", False),
        "memory_backend": getattr(agent, "memory_backend", "hybrid_semantic"),
        "memory_prompt_mode": "subtle_forum" if prompt_mode == "subtle_timeline" else prompt_mode,
        "memory_vote_signal_only": getattr(agent, "memory_vote_signal_only", True),
        "memory_reply_context_max_chars": getattr(agent, "memory_reply_context_max_chars", 220),
        "memory_search_k": getattr(agent, "memory_search_k", 8),
        "memory_search_max_chars": getattr(agent, "memory_search_max_chars", 900),
        "memory_total_max_chars": getattr(agent, "memory_total_max_chars", 1400),
        "memory_tier_a_max_chars": getattr(agent, "memory_tier_a_max_chars", 280),
        "memory_tier_b_max_chars": getattr(agent, "memory_tier_b_max_chars", 720),
        "memory_tier_c_max_chars": getattr(agent, "memory_tier_c_max_chars", 520),
        "memory_tier_c_uncertainty_threshold": getattr(
            agent, "memory_tier_c_uncertainty_threshold", 0.45
        ),
        "memory_digest_update_cadence_rounds": getattr(
            agent, "memory_digest_update_cadence_rounds", 3
        ),
        "memory_digest_events_limit": getattr(agent, "memory_digest_events_limit", 24),
        "memory_reflection_cadence_rounds": getattr(
            agent, "memory_reflection_cadence_rounds", 3
        ),
        "memory_reflection_min_events": getattr(agent, "memory_reflection_min_events", 12),
        "memory_reflection_trigger_importance_sum": getattr(
            agent, "memory_reflection_trigger_importance_sum", 3.5
        ),
        "memory_reflection_max_items_per_run": getattr(
            agent, "memory_reflection_max_items_per_run", 60
        ),
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
        "memory_pair_limit": getattr(agent, "memory_pair_limit", 8),
        "pair_history_limit": getattr(agent, "memory_pair_limit", 8),
        "thread_history_limit": getattr(agent, "memory_evidence_tail_max", 12),
        "memory_semantic_enabled": getattr(agent, "memory_semantic_enabled", True),
        "memory_embedding_model": getattr(agent, "memory_embedding_model", ""),
        "memory_embedding_async": getattr(agent, "memory_embedding_async", False),
        "memory_importance_mode": getattr(agent, "memory_importance_mode", ""),
    }
    config = MemoryConfig.from_mapping(raw)
    runtime = YClientMemoryRuntime(agent)
    engine = build_memory_engine(
        backend=str(raw["memory_backend"] or "hybrid_semantic"),
        config=config,
        runtime=runtime,
    )
    return runtime, engine
