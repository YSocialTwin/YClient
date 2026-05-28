import json

from y_client.classes.base_agent import Agent, _stress_reward_settings_from_config
from y_client.stress_reward.update_system import StressRewardSystem


class _FakeStressRewardSystem:
    def __init__(self):
        self.current_calls = []
        self.comment_calls = []
        self.share_calls = []
        self.churn_calls = []
        self.activity_calls = []

    def compute_current_stress_reward(self, **kwargs):
        self.current_calls.append(kwargs)
        return {"stress": 0.3, "reward": 0.6}

    def compute_comment_delta(self, **kwargs):
        self.comment_calls.append(kwargs)
        return {"delta_stress": 0.12, "delta_reward": -0.04}

    def compute_share_delta(self, **kwargs):
        self.share_calls.append(kwargs)
        return {"delta_stress": -0.01, "delta_reward": 0.08}

    def churn_enabled(self):
        return True

    def activity_impact_enabled(self):
        return True

    def compute_churn_probability(self, **kwargs):
        self.churn_calls.append(kwargs)
        return 0.9

    def compute_activity_effect(self, **kwargs):
        self.activity_calls.append(kwargs)
        return {"action_multiplier": 0.42, "skip_probability": 0.28}


def test_stress_reward_settings_default_to_disabled():
    assert _stress_reward_settings_from_config({})["enabled"] is False
    assert _stress_reward_settings_from_config({"simulation": {"stress_reward": {"enabled": True}}})[
        "enabled"
    ] is True


def test_stress_reward_settings_merge_nested_system_config():
    settings = _stress_reward_settings_from_config(
        {
            "stress_reward": {
                "enabled": True,
                "system": {"events": {"reaction": {"like": {"reward": 0.4}}}},
            },
            "simulation": {
                "stress_reward": {
                    "system": {"coupling": {"reward_buffers_stress_alpha": 0.1}}
                }
            },
        }
    )

    assert settings["enabled"] is True
    assert settings["system"]["events"]["reaction"]["like"]["reward"] == 0.4
    assert settings["system"]["coupling"]["reward_buffers_stress_alpha"] == 0.1


def test_stress_reward_settings_include_churn_configuration():
    settings = _stress_reward_settings_from_config(
        {
            "stress_reward": {
                "enabled": True,
                "system": {"churn": {"enabled": True, "bias": -1.1, "temperature": 0.2}},
            }
        }
    )

    assert settings["enabled"] is True
    assert settings["system"]["churn"]["enabled"] is True
    assert settings["system"]["churn"]["bias"] == -1.1
    assert settings["system"]["churn"]["temperature"] == 0.2


def test_stress_reward_system_defaults_match_hpc_adjusted_scores():
    system = StressRewardSystem()

    assert system.config["events"]["reaction"]["dislike"] == {
        "stress": 0.05,
        "reward": -0.03,
    }
    assert system.config["events"]["comment"]["critical"] == {
        "stress": 0.06,
        "reward": -0.02,
    }
    assert system.config["events"]["comment"]["hostile"] == {
        "stress": 0.14,
        "reward": -0.07,
    }
    assert system.config["events"]["report"]["mass_report"] == {
        "stress": 0.12,
        "reward": -0.05,
    }


def test_stress_reward_activity_effect_reduces_actions_for_stressed_agents():
    system = StressRewardSystem()

    effect = system.compute_activity_effect(current_stress=0.8, current_reward=0.1)

    assert 0.15 <= effect["action_multiplier"] < 1.0
    assert 0.0 < effect["skip_probability"] <= 0.65


def test_refresh_stress_reward_state_updates_agent_cache():
    agent = Agent.__new__(Agent)
    agent.user_id = 17
    agent.base_url = "http://example.test"
    agent.stress_reward_enabled = True
    agent.stress_reward_settings = {"backward_rounds": 9}
    agent.stress_reward_system = _FakeStressRewardSystem()
    agent.current_stress_reward = {"stress": 0.0, "reward": 0.0}
    agent._stress_reward_last_tid = None

    state = agent.refresh_stress_reward_state(11, force=True)

    assert state == {"stress": 0.3, "reward": 0.6}
    assert agent.current_stress == 0.3
    assert agent.current_reward == 0.6
    assert agent.stress_reward_system.current_calls == [
        {
            "base_url": "http://example.test",
            "agent_id": "17",
            "current_tid": "11",
            "backward_rounds": 9,
        }
    ]


def test_apply_stress_reward_comment_uses_annotation_and_persists_variations():
    agent = Agent.__new__(Agent)
    agent.user_id = 5
    agent.stress_reward_enabled = True
    agent.stress_reward_system = _FakeStressRewardSystem()
    agent.get_user_from_post = lambda post_id: 99
    agent.refresh_stress_reward_state = (
        lambda tid, force=False, user_id=None: {"stress": 0.25, "reward": 0.4}
    )
    agent._annotate_stress_reward_text = lambda prompt_key, text, target_user_id=None: {
        "tone": "hostile",
        "directness": 0.8,
        "support_strength": 0.0,
    }
    persisted = []
    agent._persist_stress_reward_variations = (
        lambda target_user_id, tid, delta_payload, action=None: persisted.append(
            (target_user_id, tid, delta_payload, action)
        )
        or True
    )

    applied = agent._apply_stress_reward_comment(post_id=14, text="you are wrong", tid=7)

    assert applied is True
    assert agent.stress_reward_system.comment_calls == [
        {
            "tone": "hostile",
            "current_stress": 0.25,
            "current_reward": 0.4,
            "directness": 0.8,
            "support_strength": 0.0,
        }
    ]
    assert persisted == [
        (99, 7, {"delta_stress": 0.12, "delta_reward": -0.04}, "comment:hostile")
    ]


def test_apply_stress_reward_share_maps_supportive_to_positive():
    agent = Agent.__new__(Agent)
    agent.user_id = 5
    agent.stress_reward_enabled = True
    agent.stress_reward_system = _FakeStressRewardSystem()
    agent.get_user_from_post = lambda post_id: 23
    agent.refresh_stress_reward_state = (
        lambda tid, force=False, user_id=None: {"stress": 0.1, "reward": 0.2}
    )
    agent._annotate_stress_reward_text = lambda prompt_key, text, target_user_id=None: {
        "tone": "supportive",
        "directness": 0.7,
        "support_strength": 0.9,
    }
    persisted = []
    agent._persist_stress_reward_variations = (
        lambda target_user_id, tid, delta_payload, action=None: persisted.append(
            (target_user_id, tid, delta_payload, action)
        )
        or True
    )

    applied = agent._apply_stress_reward_share(post_id=22, text="I support this", tid=8)

    assert applied is True
    assert agent.stress_reward_system.share_calls == [
        {
            "tone": "positive",
            "current_stress": 0.1,
            "current_reward": 0.2,
            "public_exposure": 0.7,
        }
    ]
    assert persisted == [
        (23, 8, {"delta_stress": -0.01, "delta_reward": 0.08}, "share:positive")
    ]


def test_evaluate_stress_reward_churn_marks_agent_left_when_probability_hits():
    agent = Agent.__new__(Agent)
    agent.user_id = 5
    agent.left_on = None
    agent.stress_reward_enabled = True
    agent.stress_reward_churn_enabled = True
    agent.stress_reward_system = _FakeStressRewardSystem()
    agent.refresh_stress_reward_state = (
        lambda tid, force=False, user_id=None: {"stress": 0.7, "reward": 0.1}
    )
    churned = []
    agent.churn_system = lambda tid: churned.append(tid) or '{"status": 200}'
    agent._stress_reward_clamp01 = Agent._stress_reward_clamp01

    class _FixedRng:
        @staticmethod
        def random():
            return 0.05

    assert agent.evaluate_stress_reward_churn(13, rng=_FixedRng()) is True
    assert agent.left_on == 13
    assert churned == [13]
    assert agent.stress_reward_system.churn_calls == [
        {"current_stress": 0.7, "current_reward": 0.1}
    ]


def test_current_stress_reward_activity_effect_updates_agent_cache():
    agent = Agent.__new__(Agent)
    agent.user_id = 5
    agent.stress_reward_enabled = True
    agent.stress_reward_system = _FakeStressRewardSystem()
    agent.refresh_stress_reward_state = (
        lambda tid, force=False, user_id=None: {"stress": 0.7, "reward": 0.1}
    )
    agent._stress_reward_clamp01 = Agent._stress_reward_clamp01

    effect = agent.current_stress_reward_activity_effect(13, force=True)

    assert effect == {"action_multiplier": 0.42, "skip_probability": 0.28}
    assert agent.stress_reward_system.activity_calls == [
        {"current_stress": 0.7, "current_reward": 0.1}
    ]
    assert agent.current_stress_reward_activity_multiplier == 0.42
    assert agent.current_stress_reward_skip_probability == 0.28


def test_stress_prompt_block_uses_five_point_likert_scale():
    agent = Agent.__new__(Agent)
    agent.stress_reward_enabled = True
    agent.refresh_stress_reward_state = lambda tid, force=False, user_id=None: {
        "stress": 0.62,
        "reward": 0.2,
    }

    prompt_block = agent._stress_prompt_block(5)

    assert "very stressed" in prompt_block
    assert "4/5" in prompt_block


def test_stress_prompt_block_is_omitted_when_feature_disabled():
    agent = Agent.__new__(Agent)
    agent.stress_reward_enabled = False

    prompt = agent._append_stress_level_to_prompt(base_prompt="Write a post", tid=8)

    assert prompt == "Write a post"
