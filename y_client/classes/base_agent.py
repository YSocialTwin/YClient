"""
Base Agent Module

This module provides the core Agent class for the Y social network simulation.
Agents represent individual users who can perform various social actions like
posting, commenting, replying, liking, following, and consuming news content.

The Agent class integrates with LLM backends to generate realistic human-like
behavior, uses recommendation systems for content and follow suggestions,
and maintains personality traits based on the Big Five model.

Classes:
    - Agent: Individual user agent with social network capabilities
    - Agents: Collection/manager for multiple Agent instances
"""

from __future__ import annotations

from y_client.recsys.ContentRecSys import ContentRecSys
from y_client.recsys.FollowRecSys import FollowRecSys
from y_client.classes.annotator import Annotator
from y_client.news_feeds.feed_reader import NewsFeed
from y_client.classes.time import SimulationSlot
from y_client.memory_runtime import build_agent_memory_engine
import y_client.opinion_dynamics as op_dynamics
from y_client import content_store
from y_client.logger import log_execution_time
import random
from requests import get, post
import json
import os
import uuid
import numpy as np
import re
import logging
from y_client.llm import AssistantAgent

try:
    from yclient_memory.contracts import (
        BrowseMemoryRequest,
        CommentMemoryEvent,
        PostMemoryEvent,
        PostStyleRequest,
        ReplyMemoryRequest,
        VoteMemoryEvent,
    )
except ImportError:
    class _MemoryContractFallback:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    BrowseMemoryRequest = _MemoryContractFallback
    CommentMemoryEvent = _MemoryContractFallback
    PostMemoryEvent = _MemoryContractFallback
    PostStyleRequest = _MemoryContractFallback
    ReplyMemoryRequest = _MemoryContractFallback
    VoteMemoryEvent = _MemoryContractFallback

__all__ = ["Agent", "Agents"]


def _json_loads_maybe(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None
    return None


def _llm_agents_enabled_from_config(config):
    agents_cfg = (config or {}).get("agents", {}) if isinstance(config, dict) else {}
    llm_agents = agents_cfg.get("llm_agents")
    return not (
        isinstance(llm_agents, list)
        and len(llm_agents) == 1
        and llm_agents[0] is None
    )


def _opinion_dynamics_from_config(config):
    if not isinstance(config, dict):
        return {}
    simulation_cfg = config.get("simulation", {})
    if isinstance(simulation_cfg, dict):
        opinion_cfg = simulation_cfg.get("opinion_dynamics")
        if isinstance(opinion_cfg, dict):
            return opinion_cfg
    opinion_cfg = config.get("opinion_dynamics")
    return opinion_cfg if isinstance(opinion_cfg, dict) else {}


def _emotion_annotation_from_config(config):
    if not isinstance(config, dict):
        return False
    simulation_cfg = config.get("simulation", {})
    if isinstance(simulation_cfg, dict) and "emotion_annotation" in simulation_cfg:
        return bool(simulation_cfg.get("emotion_annotation"))
    return bool(config.get("emotion_annotation", False))


def _memory_settings_from_config(config):
    if not isinstance(config, dict):
        return {}
    agents_cfg = config.get("agents", {})
    if not isinstance(agents_cfg, dict):
        agents_cfg = {}
    memory_cfg = config.get("memory", {})
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}

    merged = dict(memory_cfg)
    merged.update(agents_cfg)

    if "memory_enabled" not in merged:
        if "enabled" in memory_cfg:
            merged["memory_enabled"] = bool(memory_cfg.get("enabled"))
        elif "memory_enabled" in config:
            merged["memory_enabled"] = bool(config.get("memory_enabled"))

    for key, value in config.items():
        if key.startswith("memory_") and key not in merged:
            merged[key] = value

    return merged


class Agent(object):
    """
    Represents an individual user agent in the Y social network simulation.
    
    The Agent class models a social network user with demographic attributes,
    personality traits, interests, and the ability to perform various social
    actions. Agents use LLM backends to generate realistic content and make
    decisions based on their personality, interests, and political leanings.
    
    Key Features:
        - Posts original content and news articles
        - Comments on and replies to posts
        - Likes and reshares content
        - Follows and unfollows other users
        - Uses content and follow recommendation systems
        - Maintains Big Five personality traits
        - Supports multiple LLM backends for content generation
        - Can process and describe images
    
    Attributes:
        name (str): Username of the agent
        email (str): Email address
        age (int): Age of the user
        gender (str): Gender
        nationality (str): Nationality
        language (str): Primary language
        interests (list): List of topics/interests
        leaning (str): Political leaning
        education_level (str): Education level
        toxicity (str): Toxicity level ("no", "low", "medium", "high")
        Big Five personality traits: oe, co, ex, ag, ne (openness, conscientiousness, 
                                    extraversion, agreeableness, neuroticism)
        type (str): LLM model type to use (e.g., "llama3", "gpt-4")
        round_actions (int): Number of actions per time slot
        user_id (int): Unique identifier assigned by the server
    """
    
    def __init__(
        self,
        name: str,
        email: str,
        pwd: str = None,
        age: int = None,
        interests: list = None,
        leaning: str = None,
        ag_type="llama3",
        load: bool = False,
        recsys: ContentRecSys = None,
        frecsys: FollowRecSys = None,
        config: dict = None,
        big_five: dict = None,
        language: str = None,
        owner: str = None,
        education_level: str = None,
        joined_on: int = None,
        round_actions: int = 3,
        gender: str = None,
        nationality: str = None,
        toxicity: str = "no",
        api_key: str = "NULL",
        is_page: int = 0,
        daily_activity_level: int = 1,
        profession: str = None,
        opinions: dict = None,
        archetype: str = None,
        *args,
        **kwargs,
    ):
        """
        Initialize an Agent with demographic, personality, and configuration attributes.
        
        This constructor can operate in two modes:
        1. Web mode (if 'web' in kwargs): Delegates to __web_init for server-based setup
        2. Standard mode: Initializes agent locally or loads from existing state
        
        Args:
            name (str): Username for the agent (no spaces)
            email (str): Email address for the agent
            pwd (str, optional): Password for authentication. Defaults to None.
            age (int, optional): Age of the user. Defaults to None.
            interests (list, optional): List of topics/interests. Defaults to None.
            leaning (str, optional): Political leaning. Defaults to None.
            ag_type (str, optional): LLM model type (e.g., "llama3", "gpt-4"). Defaults to "llama3".
            load (bool, optional): Whether to load agent from existing state. Defaults to False.
            recsys (ContentRecSys, optional): Content recommendation system instance. Defaults to None.
            frecsys (FollowRecSys, optional): Follow recommendation system instance. Defaults to None.
            config (dict, optional): Configuration dictionary with server URLs, agent parameters,
                                    and simulation settings. Defaults to None.
            big_five (dict, optional): Big Five personality traits with keys:
                                      'oe' (openness), 'co' (conscientiousness),
                                      'ex' (extraversion), 'ag' (agreeableness),
                                      'ne' (neuroticism). Defaults to None.
            language (str, optional): Primary language for content generation. Defaults to None.
            owner (str, optional): Username of the agent owner/creator. Defaults to None.
            education_level (str, optional): Education level. Defaults to None.
            joined_on (int, optional): Timestamp when agent joined the network. Defaults to None.
            round_actions (int, optional): Number of actions per time slot. Defaults to 3.
            gender (str, optional): Gender. Defaults to None.
            nationality (str, optional): Nationality. Defaults to None.
            toxicity (str, optional): Toxicity level ("no", "low", "medium", "high").
                                     Defaults to "no".
            api_key (str, optional): API key for LLM services. Defaults to "NULL" (self-hosted).
            is_page (int, optional): Flag indicating if this is a page agent (1) or user (0).
                                    Defaults to 0.
            daily_activity_level (int, optional): Activity level multiplier. Defaults to 1.
            profession (str, optional): Professional occupation. Defaults to None.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments. 'web' key triggers web initialization mode.
        
        Raises:
            Various exceptions may be raised during server communication or if required
            configuration parameters are missing.
        """

        if "web" in kwargs:
            self.__web_init(
                name=name,
                email=email,
                pwd=pwd,
                interests=interests,
                leaning=leaning,
                ag_type=ag_type,
                load=load,
                recsys=recsys,
                age=age,
                frecsys=frecsys,
                config=config,
                big_five=big_five,
                language=language,
                owner=owner,
                education_level=education_level,
                joined_on=joined_on,
                round_actions=round_actions,
                gender=gender,
                nationality=nationality,
                toxicity=toxicity,
                api_key=api_key,
                is_page=is_page,
                daily_activity_level=daily_activity_level,
                profession=profession,
                opinions=opinions,
                archetype=archetype,
                *args,
                **kwargs,
            )
        else:
            self.topics_sentiment = ""
            self.topics_opinions = ""
            self.annotate_emotions = _emotion_annotation_from_config(config)

            self.probability_of_daily_follow = float(config["agents"][
                "probability_of_daily_follow"
            ])
            self.probability_of_secondary_follow = float(config["agents"][
                "probability_of_secondary_follow"
            ])
            self.emotions = config["posts"]["emotions"]
            self.actions_likelihood = config["simulation"]["actions_likelihood"]
            self.base_url = config["servers"]["api"].rstrip("/")
            self.llm_base = config["servers"]["llm"]
            self.content_rec_sys_name = None
            self.follow_rec_sys_name = None
            self.name = name
            self.email = email
            self.attention_window = int(config["agents"]["attention_window"])
            self.probability_of_daily_follow = float(
                config["agents"].get("probability_of_daily_follow", 0)
            )
            self.probability_of_secondary_follow = float(
                config["agents"].get("probability_of_secondary_follow", 0)
            )
            self.daily_activity_level = daily_activity_level
            self.profession = profession
            self.activity_profile = kwargs.get("activity_profile")
            self.archetype = archetype
            self.opinions = opinions
            self.opinion_dynamics = _opinion_dynamics_from_config(config)
            self.opinions_enabled = bool(self.opinion_dynamics.get("enabled", False))
            self.llm_v_config = {
                "url": config["servers"]["llm_v"],
                "api_key": config["servers"]["llm_v_api_key"]
                if (
                    config["servers"]["llm_v_api_key"] is not None
                    and config["servers"]["llm_v_api_key"] != ""
                )
                else "NULL",
                "model": config["agents"]["llm_v_agent"],
                "temperature": config["servers"]["llm_v_temperature"],
                "max_tokens": config["servers"]["llm_v_max_tokens"],
            }
            self.llm_agents_enabled = _llm_agents_enabled_from_config(config)
            self.is_page = is_page
            self.opinions = opinions
            if self.opinions is not None:
                self.opinions_enabled = True

            self.archetype = archetype

            self.opinion_dynamics = _opinion_dynamics_from_config(config)

            print(f"Loading Preexisting simulation: {load}")

            if not load:
                self.language = language
                self.type = ag_type
                self.age = age
                self.interests = interests
                self.leaning = leaning
                self.pwd = pwd
                self.oe = big_five["oe"]
                self.co = big_five["co"]
                self.ex = big_five["ex"]
                self.ag = big_five["ag"]
                self.ne = big_five["ne"]
                self.owner = owner
                self.education_level = education_level
                self.joined_on = joined_on
                sc = SimulationSlot(config)
                sc.get_current_slot()
                self.joined_on = sc.id
                self.round_actions = round_actions
                self.gender = gender
                self.nationality = nationality
                self.toxicity = toxicity
                self.daily_activity_level = daily_activity_level
                self.profession = profession
                self.opinions = opinions

                if self.opinions is not None:
                    self.opinions_enabled = True
                self.opinion_dynamics = _opinion_dynamics_from_config(config)

                self.archetype = archetype

                uid = self.__register()

                if uid is None:
                    pass
                else:
                    self.user_id = uid

            else:
                us = json.loads(self.__get_user())
                self.user_id = us["id"]
                self.type = us["user_type"]
                self.age = us["age"]

                if us["is_page"] == 0:
                    self.interests = random.randint(
                        config["agents"]["n_interests"]["min"],
                        config["agents"]["n_interests"]["max"],
                    )
                    self.interests = self.__get_interests(-1)[0]

                    if self.opinions_enabled:
                        self.opinions = self.__get_opinions()
                    else:
                        self.opinions = None
                    self.opinion_dynamics = _opinion_dynamics_from_config(config)
                    self.archetype = archetype

                else:
                    self.interests = []

                self.leaning = us["leaning"]
                self.pwd = us["password"]
                self.oe = us["oe"]
                self.co = us["co"]
                self.ex = us["ex"]
                self.ag = us["ag"]
                self.ne = us["ne"]
                self.content_rec_sys_name = us["rec_sys"]
                self.follow_rec_sys_name = us["frec_sys"]
                self.language = us["language"]
                self.owner = us["owner"]
                self.education_level = us["education_level"]
                self.round_actions = us["round_actions"]
                self.joined_on = us["joined_on"]
                self.gender = us["gender"]
                self.toxicity = us["toxicity"]
                self.nationality = us["nationality"]
                self.is_page = us["is_page"]
                self.archetype = us['archetype'] if "archetype" in us else None

            config_list = {
                "model": f"{self.type}",
                "base_url": self.llm_base,
                "timeout": 10000,
                "api_type": "open_ai",
                "api_key": api_key
                if (api_key is not None and api_key != "")
                else "NULL",
                "price": [0, 0],
            }

            self.llm_config = {
                "config_list": [config_list],
                "seed": np.random.randint(0, 100000),
                "max_tokens": config["servers"]["llm_max_tokens"],
                # max response length, -1 no limits. Imposing limits may lead to truncated responses
                "temperature": config["servers"]["llm_temperature"],
            }
            self._init_memory_config(config)
            # Prompt templates still interpolate this field on the Standard branch.
            # Keep a safe default so posting/comment flows do not fail when no
            # topic-level sentiment has been materialized yet.
            self.topics_opinions = ""
            self.topics_sentiment = ""

            # add and configure the content recsys
            self.content_rec_sys = recsys
            if self.content_rec_sys is not None:
                self.content_rec_sys.add_user_id(self.user_id)

            # add and configure the follow recsys
            self.follow_rec_sys = frecsys
            if self.follow_rec_sys is not None:
                self.follow_rec_sys.add_user_id(self.user_id)

            self.prompts = None

    def __web_init(
        self,
        name: str,
        email: str,
        pwd: str = None,
        age: int = None,
        interests: list = None,
        leaning: str = None,
        ag_type="llama3",
        load: bool = False,
        recsys: ContentRecSys = None,
        frecsys: FollowRecSys = None,
        config: dict = None,
        big_five: dict = None,
        language: str = None,
        owner: str = None,
        education_level: str = None,
        joined_on: int = None,
        round_actions: int = 3,
        gender: str = None,
        nationality: str = None,
        toxicity: str = "no",
        api_key: str = "NULL",
        is_page: int = 0,
        daily_activity_level: int = 1,
        profession: str = None,
        activity_profile: str = None,
        opinions: dict = None,
        archetype: str = None,
        *args,
        **kwargs,
    ):
        self.topics_sentiment = ""
        self.topics_opinions = ""
        self.annotate_emotions = _emotion_annotation_from_config(config)

        self.probability_of_secondary_follow = float(config["agents"][
            "probability_of_secondary_follow"
        ])
        self.probability_of_daily_follow = float(config["agents"][
                                                     "probability_of_daily_follow"
                                                 ])
        self.emotions = config["posts"]["emotions"]
        self.actions_likelihood = config["simulation"]["actions_likelihood"]
        self.base_url = config["servers"]["api"].rstrip("/")
        self.llm_base = config["servers"]["llm"]
        self.content_rec_sys_name = None
        self.follow_rec_sys_name = None
        self.content_rec_sys = None
        self.follow_rec_sys = None
        self.topics_opinions = ""
        self.topics_sentiment = ""

        self.name = name
        self.email = email
        self.attention_window = int(config["agents"]["attention_window"])
        self.probability_of_daily_follow = float(
            config["agents"].get("probability_of_daily_follow", 0)
        )
        self.probability_of_secondary_follow = float(
            config["agents"].get("probability_of_secondary_follow", 0)
        )
        self.daily_activity_level = daily_activity_level
        self.profession = profession
        self.activity_profile = activity_profile
        self.archetype = archetype
        self.opinions = opinions
        self.opinion_dynamics = _opinion_dynamics_from_config(config)
        self.opinions_enabled = bool(self.opinion_dynamics.get("enabled", False))

        if "prompts" in kwargs:
            self.prompts = kwargs["prompts"]
            # save on agent custom prompt
            if self.prompts is not None:
                content_store.save_agent_custom_prompt(self.name, self.prompts)

        self.llm_v_config = {
            "url": config["servers"]["llm_v"],
            "api_key": config["servers"]["llm_v_api_key"]
            if (
                config["servers"]["llm_v_api_key"] is not None
                and config["servers"]["llm_v_api_key"] != ""
            )
            else "NULL",
            "temperature": config["servers"]["llm_v_temperature"],
            "max_tokens": int(config["servers"]["llm_v_max_tokens"]),
        }
        self.llm_agents_enabled = _llm_agents_enabled_from_config(config)
        try:
            self.llm_v_config["model"] = config["servers"]["llm_v_agent"]
        except:
            self.llm_v_config["model"] = "minicpm-v"

        self.is_page = is_page

        if not load:
            self.language = language
            self.type = ag_type
            self.age = age
            self.interests = interests
            self.leaning = leaning
            self.pwd = pwd
            try:
                self.oe = big_five["oe"]
                self.co = big_five["co"]
                self.ex = big_five["ex"]
                self.ag = big_five["ag"]
                self.ne = big_five["ne"]

            except:
                self.oe = kwargs["oe"]
                self.co = kwargs["co"]
                self.ex = kwargs["ex"]
                self.ag = kwargs["ag"]
                self.ne = kwargs["ne"]

            self.toxicity = toxicity
            self.owner = owner
            self.education_level = education_level
            self.joined_on = joined_on
            sc = SimulationSlot(config)
            sc.get_current_slot()
            self.joined_on = sc.id
            self.round_actions = round_actions
            self.gender = gender
            self.nationality = nationality
            self.opinions = opinions
            self.archetype = archetype

            uid = self.__register()
            if uid is None:
                pass
            else:
                self.user_id = uid

        else:
            u = self.__get_user()
            us = json.loads(u)

            if "status" in us and us["status"] == 404:
                return

            self.user_id = us["id"]
            self.type = us["user_type"]
            self.age = us["age"]

            if us["is_page"] == 0:
                try:
                    self.interests = random.randint(
                        config["agents"]["n_interests"]["min"],
                        config["agents"]["n_interests"]["max"],
                    )
                    self.interests = self.__get_interests(-1)[0]
                except:
                    self.interests = interests
                    self.interests = self.__get_interests(-1)[0]
            else:
                self.interests = []

            self.leaning = us["leaning"]
            self.pwd = us["password"]
            self.oe = us["oe"]
            self.co = us["co"]
            self.ex = us["ex"]
            self.ag = us["ag"]
            self.ne = us["ne"]
            self.content_rec_sys_name = us["rec_sys"]
            self.follow_rec_sys_name = us["frec_sys"]
            self.language = us["language"]
            self.owner = us["owner"]
            self.education_level = us["education_level"]
            self.round_actions = us["round_actions"]
            self.joined_on = us["joined_on"]
            self.gender = us["gender"]
            self.toxicity = us["toxicity"]
            self.nationality = us["nationality"]
            self.is_page = int(us["is_page"])
            if self.is_page == 0:
                self.archetype = us['archetype']

            if self.opinions_enabled:
                self.opinions = self.__get_opinions()
            else:
                self.opinions = None

        config_list = {
            "model": f"{self.type}",
            "base_url": self.llm_base,
            "timeout": 10000,
            "api_type": "open_ai",
            "api_key": api_key if (api_key is not None and api_key != "") else "NULL",
            "price": [0, 0],
        }

        self.llm_config = {
            "config_list": [config_list],
            "seed": np.random.randint(0, 100000),
            "max_tokens": int(config["servers"]["llm_max_tokens"]),
            # max response length, -1 no limits. Imposing limits may lead to truncated responses
            "temperature": float(config["servers"]["llm_temperature"]),
        }
        self._init_memory_config(config)

        self.set_rec_sys(recsys, frecsys)

        # add and configure the content recsys
        if self.content_rec_sys is not None:
            self.content_rec_sys.add_user_id(self.user_id)

        # add and configure the follow recsys
        if self.follow_rec_sys is not None:
            self.follow_rec_sys.add_user_id(self.user_id)

        self._seed_initial_opinions_if_needed()
        self.prompts = None

    def __effify(self, non_f_str: str, **kwargs):
        """
        Effify the string.

        :param non_f_str: the string to effify
        :param kwargs: the keyword arguments
        :return: the effified string
        """
        kwargs["self"] = self
        return eval(f'f"""{non_f_str}"""', kwargs)

    def _has_usable_llm_config(self):
        """Return True when a concrete model is configured for chat generation."""
        try:
            if not getattr(self, "llm_agents_enabled", True):
                return False
            config_list = (self.llm_config or {}).get("config_list") or []
            if not config_list:
                return False
            model = str((config_list[0] or {}).get("model") or "").strip()
            return model.lower() not in ("", "none", "null")
        except Exception:
            return False

    def _cold_start_opinion_value(self):
        params = (self.opinion_dynamics or {}).get("parameters") or {}
        mode = str(params.get("cold_start") or "neutral").strip().lower()
        if mode == "random":
            return float(np.random.random())
        if mode == "positive":
            return 0.75
        if mode == "negative":
            return 0.25
        if mode == "author":
            return None
        return 0.5

    def _ensure_opinion_map(self):
        if isinstance(self.opinions, dict) and self.opinions:
            return
        topics = self.interests if isinstance(self.interests, list) else []
        self.opinions = {
            str(topic): float(np.random.random())
            for topic in topics
            if str(topic).strip()
        }

    @staticmethod
    def _decode_json_response(response, default=None):
        if default is None:
            default = {}
        try:
            return json.loads(response.__dict__["_content"].decode("utf-8"))
        except Exception:
            return default

    def _post_json_api(self, route, payload):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/{route.lstrip('/')}"
        return post(api_url, headers=headers, data=json.dumps(payload))

    def _get_user_opinions_map(self, user_id):
        if user_id is None:
            return {}
        response = self._post_json_api("get_user_opinions", {"user_id": int(user_id)})
        payload = self._decode_json_response(response, default={})
        if not isinstance(payload, dict):
            return {}

        parsed = {}
        for topic_name, raw_value in payload.items():
            opinion_value = raw_value
            if isinstance(raw_value, (list, tuple)) and raw_value:
                opinion_value = raw_value[0]
            elif isinstance(raw_value, dict):
                opinion_value = raw_value.get("opinion")
            try:
                parsed[str(topic_name)] = float(opinion_value)
            except (TypeError, ValueError):
                continue
        return parsed

    def _persist_user_opinions(self, opinions, *, tid, id_interacted_with=-1, id_post=-1):
        if not opinions:
            return False
        response = self._post_json_api(
            "set_user_opinions",
            {
                "user_id": int(self.user_id),
                "opinions": opinions,
                "round": int(tid),
                "id_interacted_with": int(id_interacted_with if id_interacted_with is not None else -1),
                "id_post": int(id_post if id_post is not None else -1),
            },
        )
        payload = self._decode_json_response(response, default={})
        return str(payload.get("status")) == "200"

    def _get_post_topic_names(self, post_id):
        response = self._post_json_api("get_post_topics_name", {"post_id": int(post_id)})
        payload = self._decode_json_response(response, default=[])
        if not isinstance(payload, list):
            return []
        return [str(topic) for topic in payload if str(topic).strip()]

    def _build_current_opinion_payload(self, topic_names, fallback_value=None):
        if not topic_names:
            return {}
        self._ensure_opinion_map()
        payload = {}
        for topic_name in topic_names:
            current = self.opinions.get(topic_name) if isinstance(self.opinions, dict) else None
            if current is None:
                current = fallback_value
            if current is None:
                current = self._cold_start_opinion_value()
            if current is None:
                current = 0.5
            current = max(0.0, min(1.0, float(current)))
            if isinstance(self.opinions, dict):
                self.opinions[topic_name] = current
            payload[str(topic_name)] = current
        return payload

    def _seed_initial_opinions_if_needed(self):
        if not self.opinions_enabled or self.is_page:
            return
        self._ensure_opinion_map()
        if not self.opinions:
            return
        existing = self._get_user_opinions_map(self.user_id)
        if existing:
            self.opinions.update(existing)
            return
        seed_round = getattr(self, "joined_on", None)
        try:
            seed_round = int(seed_round)
        except (TypeError, ValueError):
            seed_round = 1
        if seed_round <= 0:
            seed_round = 1
        self._persist_user_opinions(self.opinions, tid=seed_round)

    def new_opinions(self, post_id, tid, text=""):
        if not self.opinions_enabled or self.is_page:
            return
        self._ensure_opinion_map()
        if not self.opinions:
            return
        topic_names = self._get_post_topic_names(post_id)
        if not topic_names:
            return
        author_id = self.get_user_from_post(post_id)
        try:
            author_id = int(author_id)
        except (TypeError, ValueError):
            return

        author_opinions = self._get_user_opinions_map(author_id)
        if not author_opinions:
            return
        params = dict((self.opinion_dynamics or {}).get("parameters") or {})
        method_name = str((self.opinion_dynamics or {}).get("model_name") or "bounded_confidence").strip()
        update_fn = getattr(op_dynamics, method_name, op_dynamics.bounded_confidence)

        updated = {}
        for topic_name in topic_names:
            author_opinion = author_opinions.get(topic_name)
            if author_opinion is None:
                continue
            current = self.opinions.get(topic_name)
            new_value = update_fn(
                uid=self.user_id,
                x=current,
                y=float(author_opinion),
                text=text,
                topic=topic_name,
                group_classes=(self.opinion_dynamics or {}).get("opinion_groups"),
                base_url=self.base_url,
                llm_config=getattr(self, "llm_config", None),
                **params,
            )
            if new_value is None:
                new_value = current
            if new_value is None:
                new_value = self._cold_start_opinion_value()
            if new_value is None:
                new_value = 0.5
            new_value = max(0.0, min(1.0, float(new_value)))
            self.opinions[topic_name] = new_value
            updated[topic_name] = new_value

        self._persist_user_opinions(
            updated,
            tid=tid,
            id_interacted_with=author_id,
            id_post=post_id,
        )

    def _record_self_post_opinions(self, *, topic_ids=None, topic_names=None, tid):
        if not self.opinions_enabled or self.is_page:
            return
        topics = topic_names or topic_ids
        if not topics:
            return
        opinions = self._build_current_opinion_payload(topics)
        self._persist_user_opinions(
            opinions,
            tid=tid,
            id_interacted_with=self.user_id,
            id_post=-1,
        )

    def set_prompts(self, prompts):
        """
        Set the LLM prompts.

        :param prompts: the prompts
        """
        self.prompts = prompts

        try:
            # if the agent has custom prompts substitute the default ones
            aprompt = content_store.get_agent_custom_prompt(self.name)
            if aprompt:
                self.prompts[
                    "agent_roleplay"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_simple"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_base"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_comments_share"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
        except:
            pass

    def _init_memory_config(self, config):
        agents_cfg = _memory_settings_from_config(config)
        simulation_cfg = (config or {}).get("simulation", {}) if isinstance(config, dict) else {}
        self.memory_enabled = bool(agents_cfg.get("memory_enabled", False))
        self.memory_backend = str(agents_cfg.get("memory_backend") or "hybrid_semantic").strip().lower()
        self.memory_prompt_mode = str(agents_cfg.get("memory_prompt_mode") or "subtle_timeline").strip().lower()
        self.memory_vote_signal_only = bool(agents_cfg.get("memory_vote_signal_only", True))
        self.memory_reply_context_max_chars = int(agents_cfg.get("memory_reply_context_max_chars", 220))
        self.memory_nuance_enabled = bool(agents_cfg.get("memory_nuance_enabled", True))
        self.memory_nuance_min_score = float(agents_cfg.get("memory_nuance_min_score", 0.35))
        self.memory_nuance_callback_probability = float(
            agents_cfg.get("memory_nuance_callback_probability", 0.55)
        )
        self.memory_nuance_cues_max_chars = int(agents_cfg.get("memory_nuance_cues_max_chars", 320))
        self.memory_cross_thread_callback_min_score = float(
            agents_cfg.get("memory_cross_thread_callback_min_score", 0.80)
        )
        self.memory_high_affect_enabled = bool(agents_cfg.get("memory_high_affect_enabled", False))
        self.memory_high_affect_rule_threshold = float(
            agents_cfg.get("memory_high_affect_rule_threshold", 0.55)
        )
        self.memory_high_affect_uncertain_low = float(
            agents_cfg.get("memory_high_affect_uncertain_low", 0.35)
        )
        self.memory_high_affect_uncertain_high = float(
            agents_cfg.get("memory_high_affect_uncertain_high", 0.70)
        )
        self.memory_high_affect_search_k = int(agents_cfg.get("memory_high_affect_search_k", 12))
        self.memory_high_affect_max_items = int(agents_cfg.get("memory_high_affect_max_items", 6))
        self.memory_high_affect_max_chars = int(agents_cfg.get("memory_high_affect_max_chars", 900))
        self.memory_high_affect_llm_fallback = bool(
            agents_cfg.get("memory_high_affect_llm_fallback", False)
        )
        self.memory_pair_limit = int(agents_cfg.get("memory_pair_limit", 8))
        self.memory_prompt_max_chars = int(agents_cfg.get("memory_prompt_max_chars", 1600))
        self.memory_social_decay_lambda = float(agents_cfg.get("memory_social_decay_lambda", 0.05))
        self.memory_social_corruption_rate = float(
            agents_cfg.get("memory_social_corruption_rate", 0.02)
        )
        self.memory_social_resummarize_every_events = int(
            agents_cfg.get("memory_social_resummarize_every_events", 4)
        )
        self.memory_thread_decay_lambda = float(agents_cfg.get("memory_thread_decay_lambda", 0.03))
        self.memory_thread_corruption_rate = float(
            agents_cfg.get("memory_thread_corruption_rate", 0.01)
        )
        self.memory_thread_resummarize_every_events = int(
            agents_cfg.get("memory_thread_resummarize_every_events", 4)
        )
        self.memory_evidence_tail_max = int(agents_cfg.get("memory_evidence_tail_max", 8))
        self.memory_digest_update_cadence_rounds = int(
            agents_cfg.get("memory_digest_update_cadence_rounds", 3)
        )
        self.memory_digest_events_limit = int(agents_cfg.get("memory_digest_events_limit", 24))
        self.memory_cold_start_window = int(agents_cfg.get("memory_cold_start_window", 5))
        self.memory_semantic_enabled = bool(agents_cfg.get("memory_semantic_enabled", True))
        self.memory_search_k = int(agents_cfg.get("memory_search_k", 8))
        self.memory_search_max_chars = int(agents_cfg.get("memory_search_max_chars", 900))
        self.memory_search_time_window_rounds = int(
            agents_cfg.get("memory_search_time_window_rounds", 40)
        )
        self.memory_tier_a_max_chars = int(agents_cfg.get("memory_tier_a_max_chars", 280))
        self.memory_tier_b_max_chars = int(agents_cfg.get("memory_tier_b_max_chars", 720))
        self.memory_tier_c_max_chars = int(agents_cfg.get("memory_tier_c_max_chars", 520))
        self.memory_total_max_chars = int(agents_cfg.get("memory_total_max_chars", 1400))
        self.memory_tier_c_uncertainty_threshold = float(
            agents_cfg.get("memory_tier_c_uncertainty_threshold", 0.45)
        )
        self.memory_reflection_cadence_rounds = int(
            agents_cfg.get("memory_reflection_cadence_rounds", 3)
        )
        self.memory_reflection_min_events = int(
            agents_cfg.get("memory_reflection_min_events", 12)
        )
        self.memory_reflection_trigger_importance_sum = float(
            agents_cfg.get("memory_reflection_trigger_importance_sum", 3.5)
        )
        self.memory_reflection_max_items_per_run = int(
            agents_cfg.get("memory_reflection_max_items_per_run", 60)
        )
        self.memory_embedding_model = str(agents_cfg.get("memory_embedding_model") or "").strip()
        self.memory_embedding_async = bool(agents_cfg.get("memory_embedding_async", False))
        self.memory_importance_mode = str(
            agents_cfg.get("memory_importance_mode") or "heuristic_then_batch_llm"
        ).strip()
        self.memory_run_id = str(
            agents_cfg.get("memory_run_id")
            or simulation_cfg.get("name")
            or "memory_run"
        )
        self._external_memory_runtime = None
        self._external_memory_engine = None
        self._external_memory_disabled = False

    def _memory_warn(self, message):
        logging.warning("[memory][%s] %s", getattr(self, "name", "agent"), message)

    def _memory_extract_json(self, response):
        try:
            if response is None:
                return {}
            if hasattr(response, "json"):
                data = response.json()
            else:
                raw = getattr(response, "__dict__", {}).get("_content", b"")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                data = json.loads(raw or "{}")
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _memory_api_post(self, path: str, payload: dict, timeout_s: float = 4.0):
        if not getattr(self, "memory_enabled", False):
            return {}
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
            response = post(f"{api_url}", headers=headers, data=json.dumps(payload), timeout=timeout_s)
            return self._memory_extract_json(response)
        except Exception:
            return {}

    def _memory_truncate(self, text_value, max_chars):
        text = str(text_value or "").strip()
        if max_chars is None:
            return text
        try:
            max_chars = int(max_chars)
        except Exception:
            return text
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _memory_build_query_text(self, *parts):
        clean = []
        for part in parts:
            text = re.sub(r"\s+", " ", str(part or "")).strip()
            if text:
                clean.append(text)
        return " | ".join(clean)

    def _memory_fetch_context(self, *, other_user_id=None, thread_root_id=None):
        payload = {
            "run_id": self.memory_run_id,
            "agent_user_id": getattr(self, "user_id", None),
            "other_user_id": other_user_id,
            "thread_root_id": thread_root_id,
        }
        return self._memory_api_post("/memory/get_context", payload) or {}

    def _memory_search(self, **kwargs):
        payload = {
            "run_id": self.memory_run_id,
            "agent_user_id": getattr(self, "user_id", None),
        }
        payload.update(kwargs)
        return self._memory_api_post("/memory/search", payload) or {}

    def _memory_get_author_id_and_username(self, post_id: int):
        try:
            user_id = self.get_user_from_post(int(post_id))
            return (int(user_id), None) if user_id is not None else (None, None)
        except Exception:
            return None, None

    def _memory_get_thread_root_id(self, post_id: int):
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url}/get_thread_root"
            response = get(
                f"{api_url}", headers=headers, data=json.dumps({"post_id": int(post_id)})
            )
            data = self._memory_extract_json(response)
            return int(data.get("id") or data.get("post_id") or post_id)
        except Exception:
            return int(post_id)

    def _memory_get_recent_root_posts(self, tid: int, limit=24, rounds_back=18):
        return []

    def _memory_get_external_engine(self):
        if not getattr(self, "memory_enabled", False):
            return None
        if getattr(self, "_external_memory_disabled", False):
            return None
        engine = getattr(self, "_external_memory_engine", None)
        if engine is None:
            try:
                runtime, engine = build_agent_memory_engine(self)
            except Exception as exc:
                self._memory_warn(f"external engine unavailable, falling back to legacy behavior: {exc}")
                self._external_memory_disabled = True
                return None
            self._external_memory_runtime = runtime
            self._external_memory_engine = engine
        return self._memory_sync_external_engine()

    def _memory_sync_external_engine(self):
        engine = getattr(self, "_external_memory_engine", None)
        if engine is None:
            return None
        if hasattr(engine, "_fetch_context"):
            engine._fetch_context = (
                lambda *, other_user_id=None, thread_root_id=None: self._memory_fetch_context(
                    other_user_id=other_user_id,
                    thread_root_id=thread_root_id,
                ) or {}
            )
        if hasattr(engine, "_search"):
            engine._search = lambda **kwargs: self._memory_search(**kwargs) or {
                "retrieval_meta": {
                    "degraded_mode": False,
                    "embedding_degraded": False,
                    "no_ready_candidates": True,
                },
                "items": [],
            }
        return engine

    def _memory_build_reply_context(
        self,
        *,
        query_text: str,
        other_user_id=None,
        thread_root_id=None,
        other_username=None,
        round_id=None,
    ):
        engine = self._memory_get_external_engine()
        if engine is None:
            return "", {"usage": "none"}
        result = engine.build_reply_context(
            ReplyMemoryRequest(
                query_text=query_text,
                other_user_id=other_user_id,
                other_username=other_username,
                thread_root_id=thread_root_id,
                round_id=round_id,
                mode="comment",
            )
        )
        meta = {
            "search_used": bool(result.diagnostics.search_used),
            "degraded_mode": bool(result.diagnostics.degraded_mode),
            "embedding_degraded": bool(result.diagnostics.embedding_degraded),
            "no_ready_candidates": bool(result.diagnostics.no_ready_candidates),
            "retrieved_item_count": int(result.diagnostics.retrieved_item_count or 0),
            "top_score": result.diagnostics.top_score,
            "continuity_text": result.continuity_text,
        }
        return result.rendered_text, meta

    def _memory_record_event(
        self,
        *,
        tid: int,
        event_type: str,
        target_user_id=None,
        thread_root_id=None,
        target_post_id=None,
        relation_label=None,
        tone_label=None,
        topics=None,
        salient_claim=None,
        weight: float = 1.0,
    ):
        if not getattr(self, "memory_enabled", False):
            return {}
        payload = {
            "run_id": self.memory_run_id,
            "round_id": int(tid),
            "actor_user_id": int(self.user_id),
            "event_type": str(event_type).strip().lower(),
            "weight": float(weight if weight is not None else 1.0),
        }
        if target_user_id is not None:
            payload["target_user_id"] = int(target_user_id)
        if thread_root_id is not None:
            payload["thread_root_id"] = int(thread_root_id)
        if target_post_id is not None:
            payload["target_post_id"] = int(target_post_id)
        if relation_label:
            payload["relation_label"] = str(relation_label).strip().lower()[:16]
        if tone_label:
            payload["tone_label"] = str(tone_label).strip().lower()[:16]
        if topics is not None:
            payload["topics"] = topics
        if salient_claim:
            payload["salient_claim"] = str(salient_claim).strip()[:200]
        return self._memory_api_post("/memory/event", payload)

    def _memory_upsert_social_card(
        self,
        *,
        tid: int,
        other_user_id: int,
        thread_root_id=None,
        deltas: dict,
        relation_label=None,
        tone_label=None,
        salient_claim=None,
        include_evidence=True,
        count_as_event=True,
    ):
        if not getattr(self, "memory_enabled", False):
            return
        ctx = self._memory_fetch_context(other_user_id=other_user_id, thread_root_id=thread_root_id) or {}
        card = ctx.get("social_card") if isinstance(ctx, dict) else {}
        if not isinstance(card, dict):
            card = {}

        def _getf(key):
            try:
                return float(card.get(key) or 0.0)
            except Exception:
                return 0.0

        def _clip(value):
            return max(-5.0, min(5.0, float(value)))

        evidence_tail = _json_loads_maybe(card.get("evidence_tail")) if hasattr(card, "get") else None
        if not isinstance(evidence_tail, list):
            evidence_tail = []
        if include_evidence and salient_claim:
            evidence_tail.append(
                {
                    "round_id": int(tid),
                    "thread_root_id": int(thread_root_id) if thread_root_id is not None else None,
                    "relation_label": relation_label,
                    "tone_label": tone_label,
                    "salient_claim": str(salient_claim)[:200],
                }
            )
            evidence_tail = evidence_tail[-8:]

        event_count = int(card.get("event_count") or 0) if isinstance(card, dict) else 0
        if count_as_event:
            event_count += 1
        summary_bits = []
        if salient_claim:
            summary_bits.append(str(salient_claim)[:120])
        if relation_label:
            summary_bits.append(f"relation={relation_label}")
        if tone_label:
            summary_bits.append(f"tone={tone_label}")
        summary_text = "; ".join(summary_bits)[:400] if summary_bits else (card.get("summary_text") if isinstance(card, dict) else None)

        payload = {
            "run_id": self.memory_run_id,
            "agent_user_id": int(self.user_id),
            "other_user_id": int(other_user_id),
            "affinity": _clip(_getf("affinity") + float(deltas.get("affinity_delta", 0.0) or 0.0)),
            "conflict": _clip(_getf("conflict") + float(deltas.get("conflict_delta", 0.0) or 0.0)),
            "humor": _clip(_getf("humor") + float(deltas.get("humor_delta", 0.0) or 0.0)),
            "trust": _clip(_getf("trust") + float(deltas.get("trust_delta", 0.0) or 0.0)),
            "last_relation_label": relation_label,
            "last_round_id": int(tid),
            "last_thread_root_id": int(thread_root_id) if thread_root_id is not None else None,
            "last_updated_round": int(tid),
            "event_count": int(event_count),
            "summary_text": summary_text,
            "evidence_tail": evidence_tail,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        self._memory_api_post("/memory/social/upsert", payload)

    def _memory_upsert_thread_card(self, *, tid: int, thread_root_id: int, conv_text: str):
        if not getattr(self, "memory_enabled", False):
            return
        gist_text = self._memory_truncate(conv_text, 300)
        payload = {
            "run_id": self.memory_run_id,
            "agent_user_id": int(self.user_id),
            "thread_root_id": int(thread_root_id),
            "gist_text": gist_text,
            "my_role": "participant",
            "last_seen_round_id": int(tid),
        }
        self._memory_api_post("/memory/thread/upsert", payload)

    def _memory_maybe_update_community_digest(self, *, tid: int, post_text: str = ""):
        if not getattr(self, "memory_enabled", False):
            return
        if not isinstance(post_text, str) or not post_text.strip():
            return
        payload = {
            "run_id": self.memory_run_id,
            "round_id": int(tid),
            "digest_text": self._memory_truncate(
                f"Recent timeline posts include short personal takes and reactions. Latest example: {post_text}",
                400,
            ),
        }
        self._memory_api_post("/memory/community/update", payload)

    def _memory_build_thread_browse_context(self, *, thread_root_id: int, tid: int):
        engine = self._memory_get_external_engine()
        if engine is None:
            return "", {"usage": "none"}
        result = engine.build_browse_context(
            BrowseMemoryRequest(thread_root_id=thread_root_id, round_id=int(tid))
        )
        return result.rendered_text, {"usage": result.diagnostics.usage or "none"}

    def _memory_build_post_style_context(self, *, tid: int):
        engine = self._memory_get_external_engine()
        if engine is None:
            return "", {"usage": "none"}
        result = engine.build_post_style_context(PostStyleRequest(round_id=int(tid)))
        meta = {
            "usage": result.diagnostics.usage or "none",
            "root_count": int(result.diagnostics.metadata.get("root_count") or 0),
            "distinct_author_count": int(result.diagnostics.metadata.get("distinct_author_count") or 0),
            "mature": bool(result.diagnostics.metadata.get("mature", False)),
        }
        return result.rendered_text, meta

    def _memory_compose_prompt(self, base_prompt: str, *blocks):
        text = str(base_prompt or "").strip()
        extras = [str(block or "").strip() for block in blocks if str(block or "").strip()]
        if not extras:
            return text
        return f"{text}\n\n##MEMORY CONTEXT##\n" + "\n\n".join(extras) + "\n##END MEMORY CONTEXT##"

    def _memory_prompt_with_post_context(self, *, base_prompt: str, tid: int):
        memory_text, _ = self._memory_build_post_style_context(tid=int(tid))
        return self._memory_compose_prompt(base_prompt, memory_text)

    def _memory_prompt_with_comment_context(
        self,
        *,
        base_prompt: str,
        post_id: int,
        tid: int,
        conv_text: str,
    ):
        other_user_id, other_username = self._memory_get_author_id_and_username(int(post_id))
        thread_root_id = self._memory_get_thread_root_id(int(post_id))
        reply_text, _ = self._memory_build_reply_context(
            query_text=self._memory_build_query_text(conv_text),
            other_user_id=other_user_id,
            thread_root_id=thread_root_id,
            other_username=other_username,
            round_id=int(tid),
        )
        browse_text, _ = self._memory_build_thread_browse_context(
            thread_root_id=int(thread_root_id),
            tid=int(tid),
        )
        return self._memory_compose_prompt(base_prompt, reply_text, browse_text)

    def _memory_after_comment(
        self,
        *,
        tid: int,
        target_post_id: int,
        thread_root_id: int,
        other_user_id: int | None,
        other_username: str | None,
        other_text: str,
        my_text: str,
        conv_text: str,
    ):
        engine = self._memory_get_external_engine()
        if engine is not None:
            try:
                engine.record_comment(
                    CommentMemoryEvent(
                        round_id=int(tid),
                        target_post_id=int(target_post_id),
                        thread_root_id=int(thread_root_id),
                        other_user_id=int(other_user_id) if other_user_id is not None else None,
                        other_username=other_username,
                        other_text=other_text or "",
                        my_text=my_text or "",
                        conv_text=conv_text or "",
                    )
                )
            except Exception as exc:
                self._memory_warn(f"comment engine write failed: {exc}")
        relation_label = "engaged"
        tone_label = "neutral"
        deltas = {"affinity_delta": 0.35, "conflict_delta": 0.0, "humor_delta": 0.0, "trust_delta": 0.15}
        salient_claim = self._memory_truncate(my_text or other_text, 160)
        self._memory_record_event(
            tid=int(tid),
            event_type="comment",
            target_user_id=other_user_id,
            thread_root_id=thread_root_id,
            target_post_id=target_post_id,
            relation_label=relation_label,
            tone_label=tone_label,
            salient_claim=salient_claim,
            weight=1.0,
        )
        if other_user_id is not None:
            self._memory_upsert_social_card(
                tid=int(tid),
                other_user_id=int(other_user_id),
                thread_root_id=thread_root_id,
                deltas=deltas,
                relation_label=relation_label,
                tone_label=tone_label,
                salient_claim=salient_claim,
            )
        self._memory_upsert_thread_card(tid=int(tid), thread_root_id=int(thread_root_id), conv_text=conv_text or "")

    def _memory_after_vote(self, *, tid: int, post_id: int, vote_type: str):
        engine = self._memory_get_external_engine()
        if engine is not None:
            try:
                engine.record_vote(
                    VoteMemoryEvent(
                        round_id=int(tid),
                        post_id=int(post_id),
                        vote_type=str(vote_type),
                    )
                )
            except Exception as exc:
                self._memory_warn(f"vote engine write failed: {exc}")
        other_user_id, _ = self._memory_get_author_id_and_username(int(post_id))
        thread_root_id = self._memory_get_thread_root_id(int(post_id))
        if other_user_id is not None:
            if vote_type == "like":
                deltas = {"affinity_delta": 0.5, "conflict_delta": -0.1, "humor_delta": 0.0, "trust_delta": 0.2}
            else:
                deltas = {"affinity_delta": -0.3, "conflict_delta": 0.6, "humor_delta": 0.0, "trust_delta": -0.2}
            self._memory_upsert_social_card(
                tid=int(tid),
                other_user_id=int(other_user_id),
                thread_root_id=thread_root_id,
                deltas=deltas,
                relation_label="reacted",
                tone_label="positive" if vote_type == "like" else "negative",
                salient_claim=f"{vote_type} on post {int(post_id)}",
                include_evidence=not getattr(self, "memory_vote_signal_only", True),
                count_as_event=not getattr(self, "memory_vote_signal_only", True),
            )
            if not getattr(self, "memory_vote_signal_only", True):
                self._memory_record_event(
                    tid=int(tid),
                    event_type="upvote" if vote_type == "like" else "downvote",
                    target_user_id=other_user_id,
                    thread_root_id=thread_root_id,
                    target_post_id=post_id,
                    salient_claim=f"{vote_type} on post {int(post_id)}",
                    weight=0.4,
                )

    def _memory_after_post(self, *, tid: int, post_text: str, origin_kind="text_post"):
        engine = self._memory_get_external_engine()
        if engine is not None:
            try:
                engine.record_post(
                    PostMemoryEvent(
                        round_id=int(tid),
                        text=post_text or "",
                        user_id=int(getattr(self, "user_id", -1) or -1),
                        origin_kind=str(origin_kind or "text_post"),
                    )
                )
            except Exception as exc:
                self._memory_warn(f"post engine write failed: {exc}")
        salient = self._memory_truncate(post_text or "", 180)
        self._memory_record_event(
            tid=int(tid),
            event_type="post",
            salient_claim=salient,
            weight=1.0,
        )
        self._memory_maybe_update_community_digest(tid=int(tid), post_text=salient)

    def set_rec_sys(self, content_recsys, follow_recsys):
        """
        Set the recommendation systems.

        :param content_recsys: the content recommendation system
        :param follow_recsys: the follow recommendation system
        """
        if self.content_rec_sys is None:
            self.content_rec_sys = content_recsys
            self.content_rec_sys.add_user_id(self.user_id)
            self.content_rec_sys_name = content_recsys.name

            api_url = f"{self.base_url}/update_user"

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            params = {
                "username": self.name,
                "email": self.email,
                "recsys_type": content_recsys.name,
            }
            st = json.dumps(params)
            post(f"{api_url}", headers=headers, data=st)

        if self.follow_rec_sys is None:
            self.follow_rec_sys = follow_recsys
            self.follow_rec_sys.add_user_id(self.user_id)
            self.follow_rec_sys_name = follow_recsys.name

            api_url = f"{self.base_url}/update_user"

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            params = {
                "username": self.name,
                "email": self.email,
                "frecsys_type": follow_recsys.name,
            }
            st = json.dumps(params)
            post(f"{api_url}", headers=headers, data=st)

        return {"status": 200}

    def _rule_based_post_text(self, interests):
        interests = [str(i).strip() for i in (interests or []) if str(i).strip()]
        if interests:
            return f"Thoughts on {interests[0]}"
        return "Sample post"

    def _rule_based_comment_text(self):
        return "Interesting point."

    def __extract_components(self, text, c_type="hashtags"):
        """
        Extract the components from the text.

        :param text: the text to extract the components from
        :param c_type: the component type
        :return: the extracted components
        """
        # Define the regex pattern
        if c_type == "hashtags":
            pattern = re.compile(r"#\w+")
        elif c_type == "mentions":
            pattern = re.compile(r"@\w+")
        else:
            return []
        # Find all matches in the input text
        hashtags = pattern.findall(text)
        return hashtags

    def __get_user(self):
        """
        Get the user from the service.

        :return: the user
        """
        api_url = f"{self.base_url}/get_user"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"username": self.name, "email": self.email}
        st = json.dumps(params)

        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def _check_credentials(self):
        """
        Check if the credentials are correct.

        :return: the response from the service
        """
        api_url = f"{self.base_url}/user_exists"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"name": self.name, "email": self.email}

        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        data = response.json()

        if response.status_code != 200 or data.get("status") != 200:
            return json.dumps({"status": response.status_code, "error": "User not found"})
        else:
            return json.dumps({"status": 200})

    def __register(self):
        """
        Register the agent to the service.

        :return: the response from the service
        """

        st = json.dumps(
            {
                "name": self.name,
                "email": self.email,
                "password": self.pwd,
                "leaning": self.leaning,
                "age": self.age,
                "user_type": self.type,
                "oe": self.oe,
                "co": self.co,
                "ex": self.ex,
                "ag": self.ag,
                "ne": self.ne,
                "language": self.language,
                "owner": self.owner,
                "education_level": self.education_level,
                "round_actions": self.round_actions,
                "gender": self.gender,
                "nationality": self.nationality,
                "toxicity": self.toxicity,
                "joined_on": self.joined_on,
                "is_page": self.is_page,
                "daily_activity_level": self.daily_activity_level,
                "profession": self.profession,
                "activity_profile": self.activity_profile,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/register"
        post(f"{api_url}", headers=headers, data=st)

        us = self.__get_user()
        res = json.loads(us)
        uid = int(res["id"])

        api_url = f"{self.base_url}/set_user_interests"
        data = {"user_id": uid, "interests": self.interests, "round": self.joined_on}

        post(f"{api_url}", headers=headers, data=json.dumps(data))

        if self.opinions_enabled:
            api_url = f"{self.base_url}/set_user_opinions"
            data = {"user_id": uid, "opinions": self.opinions, "round": self.joined_on}
            post(f"{api_url}", headers=headers, data=json.dumps(data))

        return uid

    def __get_opinions(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/get_user_opinions"

        data = {
            "user_id": self.user_id,
        }
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data))
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        opinions = {}
        try:
            for k, v in data.items():
                opinions[k] = v[0]
        except:
            return {}

        return opinions

    def __get_interests(self, tid):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # current round
        if tid == -1:
            # get last round id
            api_url = f"{self.base_url}/current_time"
            response = get(f"{api_url}", headers=headers)
            data = json.loads(response.__dict__["_content"].decode("utf-8"))
            tid = int(data["id"])

        api_url = f"{self.base_url}/get_user_interests"

        data = {
            "user_id": self.user_id,
            "round_id": tid,
            "n_interests": self.interests
            if isinstance(self.interests, int)
            else len(self.interests),
            "time_window": self.attention_window,
        }
        response = get(f"{api_url}", headers=headers, data=json.dumps(data))

        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        try:
            # select a random interest without replacement
            if len(data) >= 3:
                selected = np.random.choice(
                    range(len(data)), np.random.randint(1, 3), replace=False
                )
            else:
                selected = np.random.choice(range(len(data)), len(data), replace=False)

            interests = [data[i]["topic"] for i in selected]
            interests_id = [data[i]["id"] for i in selected]
        except:
            return [], []

        return interests, interests_id

    def _extract_news_topics(self, article, website):
        """
        Extract topic labels for a news item so `/news` posts can participate in topic dynamics.

        :param article: the article being shared
        :param website: the source website metadata
        :return: a list of topic labels
        """
        if not self._has_usable_llm_config():
            return []

        topic_agent = AssistantAgent(
            name=f"{self.name}_topic_extractor",
            llm_config=self.llm_config,
            system_message=self.prompts["agent_roleplay_base"],
            max_consecutive_auto_reply=1,
        )

        handler = AssistantAgent(
            name="TopicHandler",
            llm_config=self.llm_config,
            system_message=self.prompts["handler_instructions_topics"],
            max_consecutive_auto_reply=1,
        )

        try:
            handler.initiate_chat(
                topic_agent,
                message=self.__effify(
                    self.prompts["handler_news"], website=website, article=article
                ),
                silent=True,
                max_round=1,
            )
            topic_eval = handler.chat_messages[topic_agent][-1]["content"]
        except Exception:
            return []
        finally:
            topic_agent.reset()
            handler.reset()

        topics = []
        for chunk in re.split(r"[;\n]+", str(topic_eval or "")):
            match = re.search(r"#T:\s*(.+)$", chunk.strip())
            if not match:
                continue
            topic = match.group(1).strip()
            if topic and "topic" not in topic.lower():
                topics.append(topic)
        return topics

    @log_execution_time
    def post(self, tid):
        """
        Post a message to the service.

        :param tid: the round id
        """

        # obtain the most recent (and frequent) interests of the agent
        interests, interests_id = self.__get_interests(tid)

        if not self._has_usable_llm_config():
            post_text = self._rule_based_post_text(interests)
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "tweet": post_text.replace('"', ""),
                    "emotions": [],
                    "hashtags": [],
                    "mentions": [],
                    "tid": tid,
                    "topics": interests_id,
                }
            )

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url}/post"
            post(f"{api_url}", headers=headers, data=st)
            self._memory_after_post(tid=int(tid), post_text=post_text, origin_kind="text_post")
            if self.opinions_enabled and interests:
                self._record_self_post_opinions(topic_names=interests, tid=int(tid))

            api_url = f"{self.base_url}/set_user_interests"
            data = {"user_id": self.user_id, "interests": interests, "round": tid}
            post(f"{api_url}", headers=headers, data=json.dumps(data))
            return

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.prompts["handler_instructions"],
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self._memory_prompt_with_post_context(
                base_prompt=self.__effify(self.prompts["handler_post"]),
                tid=int(tid),
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        post_text = u2.chat_messages[u1][-2]["content"]

        post_text = self.__clean_text(post_text)

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "tweet": post_text.replace('"', ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
                "topics": interests_id,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/post"
        post(f"{api_url}", headers=headers, data=st)
        self._memory_after_post(tid=int(tid), post_text=post_text, origin_kind="text_post")
        if self.opinions_enabled and interests:
            self._record_self_post_opinions(topic_names=interests, tid=int(tid))

        # update topic of interest with the ones used to generate the post
        api_url = f"{self.base_url}/set_user_interests"
        data = {"user_id": self.user_id, "interests": interests, "round": tid}
        post(f"{api_url}", headers=headers, data=json.dumps(data))

    @log_execution_time
    def news(self, tid, article, website):
        """
        Post a message to the service.

        :param tid: the round id
        :param article: the article
        :param website: the website
        """

        topics = self._extract_news_topics(article=article, website=website)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self._memory_prompt_with_post_context(
                base_prompt=self.__effify(
                    self.prompts["handler_news"], website=website, article=article
                ),
                tid=int(tid),
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        post_text = u2.chat_messages[u1][-2]["content"]

        post_text = (
            post_text.split(":")[-1]
            .split("-")[-1]
            .replace("@ ", "")
            .replace("  ", " ")
            .replace(". ", ".")
            .replace(" ,", ",")
            .replace("[", "")
            .replace("]", "")
            .replace("@,", "")
        )
        post_text = post_text.replace(f"@{self.name}", "")

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "tweet": post_text.replace('"', ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
                "title": article.title,
                "summary": article.summary,
                "link": article.link,
                "publisher": website.name,
                "rss": website.rss,
                "leaning": website.leaning,
                "country": website.country,
                "language": website.language,
                "category": website.category,
                "fetched_on": website.last_fetched,
                "topics": topics,
            }
        )

        u1.reset()
        u2.reset()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/news"
        res = post(f"{api_url}", headers=headers, data=st)
        self._memory_after_post(tid=int(tid), post_text=post_text, origin_kind="share_link")
        return res

    def __get_thread(self, post_id: int, max_tweets=None):
        """
        Get the thread of a post.

        :param post_id: The post id to get the thread.
        :param max_tweets: The maximum number of tweets to read for context.
        """
        api_url = f"{self.base_url}/post_thread"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))

        if isinstance(res, dict) and "error" in res:
            return res

        if max_tweets is not None and len(res) > max_tweets:
            return res[-max_tweets:]

        return res

    def get_user_from_post(self, post_id: int):
        """
        Get the user from a post.

        :param post_id: The post id to get the user.
        :return: the user
        """
        api_url = f"{self.base_url}/get_user_from_post"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    def __get_article(self, post_id: int):
        """
        Get the article.

        :param post_id: The article id to get the article.
        :return: the article
        """
        api_url = f"{self.base_url}/get_article"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": int(post_id)}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        if response.status_code == 404:
            return None
        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    def __get_post(self, post_id: int):
        """
        Get the thread of a post.

        :param post_id: The post id to get the thread.
        :return: the post
        """
        api_url = f"{self.base_url}/get_post"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    @log_execution_time
    def comment(self, post_id: int, tid, max_length_threads=None):
        """
        Generate a comment to an existing post

        :param post_id: the post id
        :param tid: the round id
        :param max_length_threads: the maximum length of the thread to read for context
        """

        conversation = self.__get_thread(post_id, max_tweets=max_length_threads)

        conv = ""

        if "error" not in conversation:
            conv = "".join(conversation)

        if not self._has_usable_llm_config():
            post_text = self._rule_based_comment_text()
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "text": post_text,
                    "emotions": [],
                    "hashtags": [],
                    "mentions": [],
                    "tid": tid,
                }
            )

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url}/comment"
            post(f"{api_url}", headers=headers, data=st)

            response = get(
                f"{self.base_url}/get_thread_root",
                headers=headers,
                data=json.dumps({"post_id": post_id}),
            )
            data = json.loads(response.__dict__["_content"].decode("utf-8"))
            if isinstance(data, dict):
                resolved_thread_root_id = int(data.get("id") or data.get("post_id") or post_id)
            else:
                try:
                    resolved_thread_root_id = int(data)
                except Exception:
                    resolved_thread_root_id = int(post_id)
            target_post_text = self.__get_post(int(post_id))
            other_user_id, other_username = self._memory_get_author_id_and_username(int(post_id))
            self._memory_after_comment(
                tid=int(tid),
                target_post_id=int(post_id),
                thread_root_id=resolved_thread_root_id,
                other_user_id=other_user_id,
                other_username=other_username,
                other_text=target_post_text if isinstance(target_post_text, str) else "",
                my_text=post_text,
                conv_text=conv,
            )
            self.__update_user_interests(data, tid)
            if self.opinions_enabled:
                self.new_opinions(post_id, tid, post_text)
            return

        # obtain the most recent (and frequent) interests of the agent
        # interests, _ = self.__get_interests(tid)

        # get the post_id topics
        api_url = f"{self.base_url}/get_post_topics_name"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.topics_opinions = "Your opinions on the discussion topics are: "
        self.topics_sentiment = "Your sentiment on the discussion topics are: "

        if self.opinions_enabled:
            opinions = self.__get_opinions() or {}
            topic_opinions = {}
            for interest in interests:
                value = opinions.get(interest, self._cold_start_opinion_value())
                if value is None:
                    continue
                topic_opinions[interest] = op_dynamics.get_opinion_group(
                    float(value), self.opinion_dynamics["opinion_groups"]
                )

            for s in topic_opinions:
                self.topics_opinions += f"{s}: {topic_opinions[s]}\n "
            if len(topic_opinions) == 0:
                self.topics_opinions = ""

        # get the opinion on the topics (if present)

        if len(interests) > 0:
            # get recent sentiment on the selected interests
            api_url = f"{self.base_url}/get_sentiment"
            data = {"user_id": self.user_id, "interests": interests}
            response = post(
                f"{api_url}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=json.dumps(data),
            )
            sentiment = json.loads(response.__dict__["_content"].decode("utf-8"))

            for s in sentiment:
                self.topics_sentiment += f"{s['topic']}: {s['sentiment']} "
            if len(sentiment) == 0:
                self.topics_sentiment = ""

        u1 = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self._memory_prompt_with_comment_context(
                base_prompt=self.__effify(self.prompts["handler_comment"], conv=conv),
                post_id=int(post_id),
                tid=int(tid),
                conv_text=conv,
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        post_text = u2.chat_messages[u1][-2]["content"]

        # cleaning the post text of some unwanted characters
        post_text = self.__clean_text(post_text)

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text.replace('"', "")
                .replace(f"{self.name}", "")
                .replace(":", "")
                .replace("*", ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/comment"
        post(f"{api_url}", headers=headers, data=st)

        res = None
        if self.probability_of_secondary_follow > 0:
            res = self.__evaluate_follow(post_text, post_id, "follow", tid)

        # update topic of interest with the ones from the post
        # get the root post id
        api_url = f"{self.base_url}/get_thread_root"
        response = get(
            f"{api_url}", headers=headers, data=json.dumps({"post_id": post_id})
        )
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if isinstance(data, dict):
            resolved_thread_root_id = int(data.get("id") or data.get("post_id") or post_id)
        else:
            try:
                resolved_thread_root_id = int(data)
            except Exception:
                resolved_thread_root_id = int(post_id)
        target_post_text = self.__get_post(int(post_id))
        other_user_id, other_username = self._memory_get_author_id_and_username(int(post_id))
        self._memory_after_comment(
            tid=int(tid),
            target_post_id=int(post_id),
            thread_root_id=resolved_thread_root_id,
            other_user_id=other_user_id,
            other_username=other_username,
            other_text=target_post_text if isinstance(target_post_text, str) else "",
            my_text=post_text,
            conv_text=conv,
        )
        self.__update_user_interests(data, tid)

        # if not followed, test unfollow
        if self.probability_of_secondary_follow > 0 and res is None:
            self.__evaluate_follow(post_text, post_id, "unfollow", tid)

        # update opinion
        if self.opinions_enabled:
            self.new_opinions(post_id, tid, post_text)

    def __update_user_interests(self, post_id, tid):
        """
        Update the user interests based on the post topics.

        :param post_id: id of the post
        :param tid: round id
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/get_post_topics"
        data = {"post_id": post_id}
        response = get(f"{api_url}", headers=headers, data=json.dumps(data))
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if len(data) > 0:
            api_url = f"{self.base_url}/set_user_interests"
            data = {"user_id": self.user_id, "interests": data, "round": tid}
            post(f"{api_url}", headers=headers, data=json.dumps(data))

    @log_execution_time
    def share(self, post_id: int, tid):
        """
        Share a post containing a news article.

        :param post_id: the post id
        :param tid: the round id
        :return: the response from the service
        """

        article = self.__get_article(post_id)
        if "status" in article:
            return

        post_text = self.__get_post(post_id)

        if not self._has_usable_llm_config():
            share_text = self._rule_based_comment_text()
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "text": share_text.replace('"', ""),
                    "emotions": [],
                    "hashtags": [],
                    "mentions": [],
                    "tid": tid,
                }
            )

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url}/share"
            post(f"{api_url}", headers=headers, data=st)
            self._memory_after_post(tid=int(tid), post_text=share_text, origin_kind="share_link")
            if self.opinions_enabled:
                self.new_opinions(post_id, tid, share_text)
            return

        # obtain the most recent (and frequent) interests of the agent
        # interests, _ = self.__get_interests(tid)

        # get the post_id topics
        api_url = f"{self.base_url}/get_post_topics_name"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        # get the opinion on the topics (if present)
        self.topics_opinions = ""
        if len(interests) > 0:
            # get recent sentiment on the selected interests
            api_url = f"{self.base_url}/get_sentiment"
            data = {"user_id": self.user_id, "interests": interests}
            response = post(
                f"{api_url}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=json.dumps(data),
            )
            sentiment = json.loads(response.__dict__["_content"].decode("utf-8"))

            self.topics_opinions = (
                "Your opinion topics of the post you are responding to are: "
            )
            for s in sentiment:
                self.topics_opinions += f"{s['topic']}: {s['sentiment']} "
            if len(sentiment) == 0:
                self.topics_opinions = ""
        else:
            interests, _ = self.__get_interests(tid)

        u1 = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self._memory_prompt_with_post_context(
                base_prompt=self.__effify(
                    self.prompts["handler_share"], article=article, post_text=post_text
                ),
                tid=int(tid),
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        post_text = u2.chat_messages[u1][-2]["content"]

        post_text = (
            post_text.split(":")[-1]
            .split("-")[-1]
            .replace("@ ", "")
            .replace("  ", " ")
            .replace(". ", ".")
            .replace(" ,", ",")
            .replace("[", "")
            .replace("]", "")
            .replace("@,", "")
        )
        post_text = post_text.replace(f"@{self.name}", "")

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text.replace('"', ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/share"
        post(f"{api_url}", headers=headers, data=st)
        self._memory_after_post(tid=int(tid), post_text=post_text, origin_kind="share_link")
        if self.opinions_enabled:
            self.new_opinions(post_id, tid, post_text)

    @log_execution_time
    def reaction(self, post_id: int, tid: int, check_follow=True):
        """
        Generate a reaction to a post/comment.

        :param post_id: the post id
        :param tid: the round id
        :param check_follow: whether to evaluate a follow cascade action
        :return: the response from the service
        """

        post_text = self.__get_post(post_id)

        if not self._has_usable_llm_config():
            vote_type = np.random.choice(["like", "dislike"])
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": vote_type,
                    "tid": tid,
                }
            )
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            api_url = f"{self.base_url}/reaction"
            post(f"{api_url}", headers=headers, data=st)
            self._memory_after_vote(tid=int(tid), post_id=int(post_id), vote_type=vote_type)
            self.__update_user_interests(post_id, tid)
            if self.opinions_enabled:
                self.new_opinions(post_id, tid, post_text)
            return

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_reactions"], post_text=post_text
            ),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "")

        u1.reset()
        u2.reset()

        if "YES" in text.split():
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": "like",
                    "tid": tid,
                }
            )
            flag = "follow"

        elif "NO" in text.split():
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": "dislike",
                    "tid": tid,
                }
            )
            flag = "unfollow"
            # always evaluate unfollow in case of dislike
            if self.probability_of_secondary_follow > 0:
                self.__evaluate_follow(post_text, post_id, flag, tid)
        else:
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/reaction"
        post(f"{api_url}", headers=headers, data=st)
        self._memory_after_vote(tid=int(tid), post_id=int(post_id), vote_type=json.loads(st)["type"])
        if self.opinions_enabled:
            self.new_opinions(post_id, tid, post_text)

        # evaluate follow only upon explicit request
        if self.probability_of_secondary_follow > 0:
            if check_follow and flag == "follow":
                self.__evaluate_follow(post_text, post_id, flag, tid)

        # update user interests after reaction
        self.__update_user_interests(post_id, tid)

    def __evaluate_follow(self, post_text, post_id, action, tid):
        """
        Evaluate secondary follow action (tied to a given probability_of_secondary_follow)

        :param post_text: the post_text
        :param post_id: the post id
        :param action: the action, either follow or unfollow
        :param tid: the round id
        :return: the response from the service
        """

        if self.probability_of_secondary_follow > 0:
            if np.random.rand() > self.probability_of_secondary_follow:
                return None
        else:
            return None

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_follow"], post_text=post_text, action=action
            ),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "")

        u1.reset()
        u2.reset()

        if "YES" in text.split():
            if action == "follow":
                self.follow(post_id=post_id, action=action, tid=tid)
                return action
            else:
                self.follow(post_id=post_id, action=action, tid=tid)
                return action
        else:
            return None

    @log_execution_time
    def follow(
        self, tid: int, target: int = None, post_id: int = None, action="follow"
    ):
        """
        Follow a user

        :param tid: the round id
        :param action: the action, either follow or unfollow
        :param post_id: the post id
        :param post_id: the post id
        :param target: the target user id
        """

        if post_id is not None:
            target = self.get_user_from_post(post_id)

        if isinstance(target, int):

            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "target": int(target),
                    "action": action,
                    "tid": tid,
                }
            )

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            api_url = f"{self.base_url}/follow"
            post(f"{api_url}", headers=headers, data=st)

    def followers(self):
        """
        Get the followers of the user.

        :return: the response from the service
        """

        st = json.dumps({"user_id": self.user_id})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/followers"
        response = get(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def timeline(self):
        """
        Get the timeline of the user.

        :return: the response from the service
        """

        st = json.dumps({"user_id": self.user_id})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/timeline"
        response = get(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    @log_execution_time
    def cast(self, post_id: int, tid: int):
        """
        Cast a voting intention (political simulation)

        :param post_id: the post id
        :param tid: the round id
        :return: the response from the service
        """

        post_text = self.__get_post(post_id)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_cast"], post_text=post_text),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()

        u1.reset()
        u2.reset()

        data = {
            "user_id": self.user_id,
            "post_id": post_id,
            "content_type": "Post",
            "tid": tid,
            "content_id": post_id,
        }

        if "RIGHT" in text.split():
            data["vote"] = "R"
            st = json.dumps(data)

        elif "LEFT" in text.split():
            data["vote"] = "D"
            st = json.dumps(data)

        elif "NONE" in text.split():
            data["vote"] = "U"
            st = json.dumps(data)
        else:
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/cast_preference"
        post(f"{api_url}", headers=headers, data=st)

    def churn_system(self, tid):
        """
        Leave the system.

        :return:
        """
        st = json.dumps({"user_id": self.user_id, "left_on": tid})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/churn"
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    @log_execution_time
    def select_action(self, tid, actions, max_length_thread_reading=5):
        """
        Post a message to the service.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """
        if not self._has_usable_llm_config():
            return self.select_action_lite(
                tid=tid,
                actions=actions,
                max_length_thread_reading=max_length_thread_reading,
            )

        np.random.shuffle(actions)
        acts = ",".join(actions)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_base"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_action"], actions=acts),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()
        u1.reset()
        u2.reset()

        if "COMMENT" in text.split():
            candidates = json.loads(self.read())
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif "POST" in text.split():
            self.post(tid=tid)

        elif "READ" in text.split():
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.reaction(int(selected_post[0]), tid=tid)
            except:
                pass

        elif "SEARCH" in text.split():
            candidates = json.loads(self.search())
            if "status" not in candidates and len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif "FOLLOW" in text.split():
            if self.probability_of_daily_follow > 0:
                candidates = self.search_follow()
                if len(candidates) > 0:
                    tot = sum([float(v) for v in candidates.values()])
                    probs = [v / tot for v in candidates.values()]
                    selected = np.random.choice(
                        [int(c) for c in candidates],
                        p=probs,
                        size=1,
                    )[0]
                    self.follow(tid=tid, target=selected, action="follow")

        elif "SHARE" in text.split():
            candidates = json.loads(self.read(article=True))
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.share(int(selected_post[0]), tid=tid)

        elif "CAST" in text.split():
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.cast(int(selected_post[0]), tid=tid)
            except:
                pass

        elif "IMAGE" in text.split():
            image, article_id = self.select_image(tid=tid)
            if image is not None:
                self.comment_image(image, tid=tid, article_id=article_id)

        return

    def select_action_lite(self, tid, actions, max_length_thread_reading=5):
        """
        Rule-based fallback for simulations without configured LLM agents.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """
        if len(actions) == 0:
            return
        action = np.random.choice(actions)

        if action == "COMMENT":
            candidates = json.loads(self.read())
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif action == "POST":
            self.post(tid=tid)

        elif action == "READ":
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.reaction(int(selected_post[0]), tid=tid)
            except:
                pass

        elif action == "SEARCH":
            candidates = json.loads(self.search())
            if "status" not in candidates and len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif action == "FOLLOW":
            if self.probability_of_daily_follow > 0:
                candidates = self.search_follow()
                if len(candidates) > 0:
                    tot = sum([float(v) for v in candidates.values()])
                    probs = [v / tot for v in candidates.values()]
                    selected = np.random.choice(
                        [int(c) for c in candidates],
                        p=probs,
                        size=1,
                    )[0]
                    self.follow(tid=tid, target=selected, action="follow")

        elif action == "SHARE":
            candidates = json.loads(self.read(article=True))
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.share(int(selected_post[0]), tid=tid)

        elif action == "CAST":
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.cast(int(selected_post[0]), tid=tid)
            except:
                pass

        elif action == "IMAGE":
            image, article_id = self.select_image(tid=tid)
            if image is not None:
                self.comment_image(image, tid=tid, article_id=article_id)

        return

    @log_execution_time
    def reply(self, tid: int, max_length_thread_reading: int = 5):
        """
        Reply to a mention.

        :param tid:
        :param max_length_thread_reading:
        :return:
        """
        selected_post = json.loads(self.read_mentions())
        if "status" not in selected_post:
            if len(selected_post) > 0:
                self.comment(
                    int(selected_post['post_id']),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
        return

    @log_execution_time
    def read(self, article=False):
        """
        Read n_posts from the service.

        :param article: Whether to read an article or not
        :return: the response from the service
        """
        return self.content_rec_sys.read(self.base_url, self.user_id, article)

    def read_mentions(self):
        """
        Read n_posts from the service.

        :return: The response from the service
        """
        return self.content_rec_sys.read_mentions(self.base_url)

    @log_execution_time
    def search(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.content_rec_sys.search(self.base_url)

    @log_execution_time
    def search_follow(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.follow_rec_sys.follow_suggestions(self.base_url)

    def select_news(self):
        """
        Select a news article from the service.

        :return: the response from the service
        """

        # Select websites with the same leaning of the agent
        website = content_store.get_random_website_by_leaning(self.leaning)
        if website is None:
            return "", ""

        # Select a random article
        website_feed = NewsFeed(website.name, website.rss)
        website_feed.read_feed()
        article = website_feed.get_random_news()
        return article, website

    def select_image(self, tid):
        """
        Select an image

        :return: the response from the service
        """
        image = content_store.get_random_image()

        # @Todo: add the case of no news sharing enabled
        if (
            "news" not in self.actions_likelihood
            or self.actions_likelihood["news"] == 0
        ):
            if image is None:
                # where to get the image from??
                return None, None
            else:
                if image.description is not None:
                    return image, None

                else:
                    # annotate the image with a description
                    an = Annotator(config=self.llm_v_config)
                    description = an.annotate(image.url)
                    content_store.save_image_description(image.id, description)

                    return image, None

        # the news module is active: images will be selected among RSS shared articles
        else:
            # no image available, select a news article and extract image from it
            if image is None:
                news, website = self.select_news()

                if news == "":
                    return None, None

                res = self.news(tid=tid, article=news, website=website)
                article_id = int(
                    json.loads(res.__dict__["_content"].decode("utf-8"))["article_id"]
                )

                image = content_store.get_image_by_article_id(article_id)

                if image is None:
                    return None, None
                else:
                    image = content_store.save_image_remote_article(image.id, article_id)

                    an = Annotator(self.llm_v_config)
                    description = an.annotate(image.url)
                    image = content_store.save_image_description(image.id, description)

                    return image, article_id

            # images available, check if they have a description
            else:
                # check if the image has a remote article id
                if image.remote_article_id is None:
                    _, article, website = content_store.get_image_with_article_and_website(
                        image.id
                    )
                    if article is None or website is None:
                        return None, None

                    # save the website and article on the server
                    st = json.dumps(
                        {
                            "user_id": self.user_id,
                            "tweet": "",
                            "emotions": [],
                            "hashtags": [],
                            "mentions": [],
                            "tid": tid,
                            "title": article.title,
                            "summary": article.summary,
                            "link": article.link,
                            "publisher": website.name,
                            "rss": website.rss,
                            "leaning": website.leaning,
                            "country": website.country,
                            "language": website.language,
                            "category": website.category,
                            "fetched_on": website.last_fetched,
                        }
                    )

                    headers = {"Content-Type": "application/x-www-form-urlencoded"}

                    api_url = f"{self.base_url}/news"
                    res = post(f"{api_url}", headers=headers, data=st)
                    remote_article_id = int(
                        json.loads(res.__dict__["_content"].decode("utf-8"))[
                            "article_id"
                        ]
                    )
                    image = content_store.save_image_remote_article(
                        image.id, remote_article_id
                    )

                if image.description is not None:
                    return image, image.remote_article_id

                else:
                    an = Annotator(config=self.llm_v_config)
                    description = an.annotate(image.url)
                    image = content_store.save_image_description(image.id, description)

                    return image, image.remote_article_id

    @log_execution_time
    def comment_image(self, image: object, tid: int, article_id: int = None):
        """
        Comment on an image

        :param image:
        :param tid:
        :param article_id:
        :return:
        """
        # obtain the most recent (and frequent) interests of the agent
        interests, _ = self.__get_interests(tid)

        self.topics_opinions = ""

        u1 = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self._memory_prompt_with_post_context(
                base_prompt=self.__effify(
                    self.prompts["handler_comment_image"], descr=image.description
                ),
                tid=int(tid),
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        post_text = u2.chat_messages[u1][-2]["content"]
        post_text = self.__clean_text(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "text": post_text.replace('"', "")
                .replace(f"{self.name}", "")
                .replace(":", "")
                .replace("*", ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "tid": tid,
                "image_url": image.url,
                "image_description": image.description,
                "article_id": article_id,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/comment_image"
        post(f"{api_url}", headers=headers, data=st)
        self._memory_after_post(tid=int(tid), post_text=post_text, origin_kind="share_image")

    def new_opinions(self, post_id: int, tid: int, text: str):
        """
        Get new opinions for a given post.

        :param post_id: The post id.
        :param tid: The round id.
        :param text: The text of the post.
        :return: The new opinions.
        """
        # get post topics
        api_url = f"{self.base_url}/get_post_topics"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        # get author of the post
        api_url = f"{self.base_url}/get_post_author"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        author_data = json.loads(response.__dict__["_content"].decode("utf-8"))
        author_id = author_data.get("user_id", None)

        # get opinions of the author on the topics
        api_url = f"{self.base_url}/get_user_opinions"
        data = {"user_id": author_id}
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        opinions = json.loads(response.__dict__["_content"].decode("utf-8"))

        # filter opinions to keep only those related to the post topics
        filtered_opinions = {
            v[1]: v[0]
            for t, v in opinions.items()
            if int(v[1]) in interests
        }

        # get recent opinions of the agents on the topics
        api_url = f"{self.base_url}/get_user_opinions"
        data = {"user_id": self.user_id}
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        agent_opinions = json.loads(response.__dict__["_content"].decode("utf-8"))

        # filter agent opinions to keep only those related to the post topics
        agent_filtered_opinions = {
            v[1]: v[0]
            for t, v in agent_opinions.items()
            if int(v[1]) in interests
        }

        filtered_topics = {
            v[1]: t
            for t, v in agent_opinions.items()
            if int(v[1]) in interests
        }

        method_name = self.opinion_dynamics['model_name']
        update = getattr(op_dynamics, method_name)

        for topic, opinion in filtered_opinions.items():
            if topic in agent_filtered_opinions:
                # update the opinion as the average of the two
                tp_name = filtered_topics[topic]

                agent_filtered_opinions[topic] = update(uid=self.user_id, x=agent_filtered_opinions[topic], y=opinion,
                                                        text=text, topic=tp_name,
                                                        **self.opinion_dynamics['parameters'],
                                                        group_classes=self.opinion_dynamics['opinion_groups'],
                                                        base_url=self.base_url, llm_config=self.llm_config)

        # set the new opinions
        api_url = f"{self.base_url}/set_user_opinions"

        data = {
                "user_id": self.user_id,
                "opinions": agent_filtered_opinions,
                "id_post": int(post_id),
                "id_interacted_with": int(author_id),
                "round": int(tid),
            }

        post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )

        return True

    def __str__(self):
        """
        Return a string representation of the Agent object.

        :return: the string representation
        """
        return f"Name: {self.name}, Age: {self.age}, Type: {self.type}"

    def __dict__(self):
        """
        Return a dictionary representation of the Agent object.

        :return: the dictionary representation
        """

        interests = self.__get_interests(-1)
        opinions = getattr(self, "opinions", None)
        if getattr(self, "opinions_enabled", False) and getattr(self, "user_id", None) is not None:
            try:
                fetched_opinions = self.__get_opinions()
                if fetched_opinions:
                    opinions = fetched_opinions
                    self.opinions = fetched_opinions
            except Exception:
                pass

        return {
            "name": self.name,
            "email": self.email,
            "password": self.pwd,
            "age": self.age,
            "type": self.type,
            "leaning": self.leaning,
            "interests": interests,
            "oe": self.oe,
            "co": self.co,
            "ex": self.ex,
            "ag": self.ag,
            "ne": self.ne,
            "rec_sys": self.content_rec_sys_name,
            "frec_sys": self.follow_rec_sys_name,
            "language": self.language,
            "owner": self.owner,
            "education_level": self.education_level,
            "round_actions": self.round_actions,
            "gender": self.gender,
            "nationality": self.nationality,
            "toxicity": self.toxicity,
            "joined_on": self.joined_on,
            "is_page": self.is_page,
            "daily_activity_level": getattr(self, "daily_activity_level", 1),
            "profession": getattr(self, "profession", None),
            "activity_profile": getattr(self, "activity_profile", None),
            "archetype": getattr(self, "archetype", None),
            "opinions": opinions,
        }

    def __emotion_annotation(self, text_to_annotate: str):
        """
        Annotate the emotions in the text.

        :param text_to_annotate: the text to annotate
        :return: the annotated emotions as a list
        """
        emotion_agent = AssistantAgent(
            name="EmotionAnnotator",
            llm_config=self.llm_config,
            system_message=self.prompts["handler_instructions"],
            max_consecutive_auto_reply=1,
        )

        prompt = (
            f"Annotate the following text with the emotions it elicits:\n\n"
            f"{text_to_annotate}. Answer with a JSON formatted list of emotions only."
        )
        response = emotion_agent._generate_reply(prompt)

        emotion_eval = response.lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        return emotion_eval

    def __clean_emotion(self, text):
        try:
            emotion_eval = [
                e.strip()
                for e in text.replace("'", " ")
                .replace('"', " ")
                .replace("*", "")
                .replace(":", " ")
                .replace("[", " ")
                .replace("]", " ")
                .replace(",", " ")
                .split(" ")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []
        return emotion_eval

    def __clean_text(self, text):
        text = (
            text.split("##")[-1]
            .replace("-", "")
            .replace("@ ", "")
            .replace("  ", " ")
            .replace(". ", ".")
            .replace(" ,", ",")
            .replace("[", "")
            .replace("]", "")
            .replace("@,", "")
            .strip("()[]{}'")
            .lstrip()
        )
        text = text.replace(f"@{self.name}", "")
        return text


class Agents(object):
    def __init__(self):
        """
        Initialize the Agent object.
        """
        self.agents = []

    def add_agent(self, agent: Agent):
        """
        Add a profile to the Agents object.

        :param agent: The Profile object to add.
        """
        self.agents.append(agent)

    def remove_agent(self, agent: Agent):
        """
        Remove a profile from the Agents object.

        :param agent: The Profile object to remove.
        """
        self.agents.remove(agent)

    def remove_agent_by_ids(self, agent_ids: list):
        """
        Remove a profile from the Agents object.

        :param agent: The Profile object to remove.
        """
        agent_ids = {int(aid): None for aid in agent_ids}
        for agent in self.agents:
            if agent.user_id in agent_ids:
                self.agents.remove(agent)

    def get_agents(self):
        return self.agents

    def agents_iter(self):
        """
        Iterate over the agents.
        """
        for agent in self.agents:
            yield agent

    def __str__(self):
        """
        Return a string representation of the Agents object.

        :return: the string representation
        """
        return "".join([p.__str__() for p in self.agents])

    def __dict__(self):
        """
        Return a dictionary representation of the Agents object.

        :return: the dictionary representation
        """
        return {"agents": [p.__dict__() for p in self.agents]}

    def __eq__(self, other):
        """
        Return True if the Agents objects are equal.

        :param other: The other agent object to compare.
        :return: True if the Agents objects are equal.
        """
        return self.__dict__() == other.__dict__()
