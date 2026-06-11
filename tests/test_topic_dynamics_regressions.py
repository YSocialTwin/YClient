from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

fake_autogen = types.ModuleType("autogen")
fake_autogen.AssistantAgent = object
fake_agentchat = types.ModuleType("autogen.agentchat")
fake_contrib = types.ModuleType("autogen.agentchat.contrib")
fake_multimodal = types.ModuleType("autogen.agentchat.contrib.multimodal_conversable_agent")
fake_multimodal.MultimodalConversableAgent = object
fake_yclient_memory = types.ModuleType("yclient_memory")
fake_contracts = types.ModuleType("yclient_memory.contracts")


class _DummyContract:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

sys.modules.setdefault("autogen", fake_autogen)
sys.modules.setdefault("autogen.agentchat", fake_agentchat)
sys.modules.setdefault("autogen.agentchat.contrib", fake_contrib)
sys.modules.setdefault(
    "autogen.agentchat.contrib.multimodal_conversable_agent",
    fake_multimodal,
)
for contract_name in [
    "BrowseMemoryRequest",
    "CommentMemoryEvent",
    "PostMemoryEvent",
    "PostStyleRequest",
    "ReplyMemoryRequest",
    "VoteMemoryEvent",
]:
    setattr(fake_contracts, contract_name, _DummyContract)

sys.modules.setdefault("yclient_memory", fake_yclient_memory)
sys.modules.setdefault("yclient_memory.contracts", fake_contracts)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import y_client.classes.base_agent as base_agent_module
import y_client.classes.fake_base_agent as fake_base_agent_module
from y_client.classes.base_agent import Agent
from y_client.classes.fake_base_agent import FakeAgent
from y_client.recsys.ContentRecSys import ContentRecSys


class FakeAssistantAgent:
    def __init__(self, name, llm_config, system_message, max_consecutive_auto_reply=1):
        self.name = name
        self.llm_config = llm_config
        self.system_message = system_message
        self.chat_messages = {}

    def initiate_chat(self, other, message, silent=True, max_round=1):
        if "Detect 3 general topic" in self.system_message:
            self.chat_messages[other] = [
                {"content": "generated news post"},
                {"content": "#T: Climate Change; #T: Energy Policy; #T: Economic Impact"},
            ]
            return

        self.chat_messages[other] = [
            {"content": "generated news post"},
            {"content": "curiosity"},
        ]

    def reset(self):
        return None


def make_content_agent() -> Agent:
    agent = Agent.__new__(Agent)
    agent.name = "tester"
    agent.user_id = 11
    agent.base_url = "http://example.test"
    agent.llm_config = {"config_list": []}
    agent.prompts = {
        "agent_roleplay": "Act as requested.",
        "agent_roleplay_base": "Act as requested.",
        "agent_roleplay_simple": "Act as requested.",
        "agent_roleplay_comments_share": "Interests: {','.join(interest)}",
        "handler_instructions_topics": "Detect 3 general topic discussed in the input text",
        "handler_instructions": "Annotate emotions",
        "handler_post": "Write a post.",
        "handler_comment": "{conv}",
        "handler_news": "Website: {website.name} Title: {article.title} Summary: {article.summary}",
        "handler_comment_image": "Description: {descr}",
    }
    agent.language = "english"
    agent.toxicity = "no"
    agent._memory_after_post = lambda **kwargs: None
    agent._memory_prompt_with_post_context = lambda base_prompt, tid: base_prompt
    agent._Agent__clean_emotion = lambda text: text
    agent._Agent__extract_components = lambda text, c_type="hashtags": []
    agent._has_usable_llm_config = lambda: True
    return agent


def test_agent_news_payload_includes_extracted_topics(monkeypatch):
    agent = make_content_agent()
    payloads = []

    monkeypatch.setattr(base_agent_module, "AssistantAgent", FakeAssistantAgent)
    monkeypatch.setattr(
        base_agent_module,
        "post",
        lambda url, headers=None, data=None: payloads.append((url, json.loads(data))) or SimpleNamespace(status_code=200),
    )

    article = SimpleNamespace(title="Climate bill", summary="Energy reform plan", link="https://example.test/a")
    website = SimpleNamespace(
        name="Example News",
        rss="https://example.test/rss",
        leaning="center",
        country="IT",
        language="en",
        category="politics",
        last_fetched="2026-03-25",
    )

    agent.news(tid=3, article=article, website=website)

    assert payloads
    assert payloads[-1][0].endswith("/news")
    assert payloads[-1][1]["topics"] == [
        "Climate Change",
        "Energy Policy",
        "Economic Impact",
    ]


def test_comment_image_prompt_keeps_current_interests(monkeypatch):
    agent = make_content_agent()
    created_messages = []

    class TopicAwareAssistant(FakeAssistantAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_messages.append(self.system_message)

    monkeypatch.setattr(base_agent_module, "AssistantAgent", TopicAwareAssistant)
    monkeypatch.setattr(
        base_agent_module,
        "post",
        lambda url, headers=None, data=None: SimpleNamespace(status_code=200),
    )
    monkeypatch.setattr(agent, "_Agent__get_interests", lambda tid: (["climate", "energy"], [1, 2]))

    image = SimpleNamespace(url="https://example.test/image.png", description="A wind farm at sunset")
    agent.comment_image(image=image, tid=4, article_id=7)

    assert any("climate,energy" in message for message in created_messages)


def test_extract_news_topics_parses_hash_t_prefix():
    agent = make_content_agent()
    base_agent_module.AssistantAgent = FakeAssistantAgent

    topics = agent._extract_news_topics(
        article=SimpleNamespace(title="Climate bill", summary="Energy reform plan"),
        website=SimpleNamespace(name="Example News"),
    )

    assert topics == [
        "Climate Change",
        "Energy Policy",
        "Economic Impact",
    ]


def test_select_image_promotes_news_image_to_remote_article(monkeypatch):
    agent = make_content_agent()
    agent.actions_likelihood = {"news": 0.5}
    agent.llm_v_config = {
        "model": "minicpm-v:latest",
        "url": "http://127.0.0.1:11434/v1",
        "api_key": "EMPTY",
        "temperature": 0.2,
        "max_tokens": 128,
    }
    image = SimpleNamespace(
        id=9,
        url="https://example.test/image.png",
        description=None,
        remote_article_id=None,
    )
    article = SimpleNamespace(
        id=4,
        title="Climate bill",
        summary="Energy reform plan",
        link="https://example.test/a",
    )
    website = SimpleNamespace(
        name="Example News",
        rss="https://example.test/rss",
        leaning="center",
        country="IT",
        language="en",
        category="politics",
        last_fetched="2026-03-25",
    )

    payloads = []

    monkeypatch.setattr(base_agent_module.content_store, "get_random_image", lambda: image)
    monkeypatch.setattr(
        base_agent_module.content_store,
        "get_image_with_article_and_website",
        lambda image_id: (image, article, website),
    )
    monkeypatch.setattr(
        base_agent_module.content_store,
        "save_image_remote_article",
        lambda image_id, remote_article_id: SimpleNamespace(
            id=image_id,
            url=image.url,
            description=image.description,
            remote_article_id=remote_article_id,
        ),
    )
    monkeypatch.setattr(
        base_agent_module,
        "post",
        lambda url, headers=None, data=None: payloads.append((url, json.loads(data)))
        or SimpleNamespace(_content=b'{"article_id": 33}'),
    )

    class FakeAnnotator:
        def __init__(self, config):
            self.config = config

        def annotate(self, image_url):
            return "A wind farm at sunset"

    monkeypatch.setattr(base_agent_module, "Annotator", FakeAnnotator)
    monkeypatch.setattr(
        base_agent_module.content_store,
        "save_image_description",
        lambda image_id, description: SimpleNamespace(
            id=image_id,
            url=image.url,
            description=description,
            remote_article_id=33,
        ),
    )

    selected_image, article_id = agent.select_image(tid=5)

    assert payloads
    assert payloads[-1][0].endswith("/news")
    assert article_id == 33
    assert selected_image.description == "A wind farm at sunset"
    assert selected_image.remote_article_id == 33


def test_fake_select_image_promotes_news_image_to_remote_article(monkeypatch):
    agent = FakeAgent.__new__(FakeAgent)
    agent.user_id = 11
    agent.base_url = "http://example.test"
    agent.actions_likelihood = {"news": 0.5}
    agent.llm_v_config = {
        "model": "minicpm-v:latest",
        "url": "http://127.0.0.1:11434/v1",
        "api_key": "EMPTY",
        "temperature": 0.2,
        "max_tokens": 128,
    }
    article = SimpleNamespace(
        title="Climate bill",
        summary="Energy reform plan",
        link="https://example.test/a",
    )
    website = SimpleNamespace(
        name="Example News",
        rss="https://example.test/rss",
        leaning="center",
        country="IT",
        language="en",
        category="politics",
        last_fetched="2026-03-25",
    )
    image = SimpleNamespace(
        id=9,
        url="https://example.test/image.png",
        description=None,
        remote_article_id=None,
    )
    payloads = []

    monkeypatch.setattr(agent, "select_news", lambda: (article, website))
    monkeypatch.setattr(
        agent,
        "news",
        lambda tid, article, website: SimpleNamespace(
            _content=b'{"article_id": 44}'
        ),
    )
    monkeypatch.setattr(
        fake_base_agent_module.content_store,
        "get_random_image",
        lambda: None,
    )
    monkeypatch.setattr(
        fake_base_agent_module.content_store,
        "get_image_by_article_id",
        lambda article_id: image,
    )
    monkeypatch.setattr(
        fake_base_agent_module.content_store,
        "save_image_remote_article",
        lambda image_id, remote_article_id: SimpleNamespace(
            id=image_id,
            url=image.url,
            description=image.description,
            remote_article_id=remote_article_id,
        ),
    )

    class FakeAnnotator:
        def __init__(self, config):
            self.config = config

        def annotate(self, image_url):
            payloads.append(image_url)
            return "A skyline photo"

    monkeypatch.setattr(fake_base_agent_module, "Annotator", FakeAnnotator)
    monkeypatch.setattr(
        fake_base_agent_module.content_store,
        "save_image_description",
        lambda image_id, description: SimpleNamespace(
            id=image_id,
            url=image.url,
            description=description,
            remote_article_id=44,
        ),
    )

    selected_image, article_id = agent.select_image(tid=5)

    assert payloads == ["https://example.test/image.png"]
    assert article_id == 44
    assert selected_image.description == "A skyline photo"
    assert selected_image.remote_article_id == 44


def test_content_recsys_clears_article_flag_between_reads(monkeypatch):
    recsys = ContentRecSys()
    calls = []

    import importlib

    content_recsys_module = importlib.import_module("y_client.recsys.ContentRecSys")

    monkeypatch.setattr(
        content_recsys_module,
        "post",
        lambda url, headers=None, data=None: calls.append(json.loads(data))
        or SimpleNamespace(_content=b"[]"),
    )

    recsys.read("http://example.test", user_id=7, articles=True)
    recsys.read("http://example.test", user_id=7, articles=False)

    assert calls[0]["articles"] is True
    assert "articles" not in calls[1]


def test_comment_payload_keeps_post_text_separate_from_emotion_annotations(monkeypatch):
    agent = make_content_agent()
    agent.annotate_emotions = True
    agent.opinions_enabled = False
    agent.probability_of_secondary_follow = 0.0
    agent._Agent__get_thread = lambda post_id, max_tweets=None: ["Root post\n"]
    agent._has_usable_llm_config = lambda: True

    payloads = []

    class CommentAssistant(FakeAssistantAgent):
        def initiate_chat(self, other, message, silent=True, max_round=1):
            if self.name == "Handler":
                self.chat_messages[other] = [
                    {"content": "I think this policy is wrong."},
                    {"content": "No emotions were found in this annotated sentence."},
                ]
            else:
                self.chat_messages[other] = [{"content": "I think this policy is wrong."}]

    monkeypatch.setattr(base_agent_module, "AssistantAgent", CommentAssistant)
    monkeypatch.setattr(
        base_agent_module,
        "post",
        lambda url, headers=None, data=None: payloads.append((url, json.loads(data)))
        or SimpleNamespace(_content=b'{"status": "200"}'),
    )
    monkeypatch.setattr(
        base_agent_module,
        "get",
        lambda *args, **kwargs: SimpleNamespace(_content=b"[]"),
    )
    monkeypatch.setattr(agent, "_Agent__emotion_annotation", lambda text: ["anger"])
    monkeypatch.setattr(agent, "_Agent__clean_text", lambda text: text)
    monkeypatch.setattr(agent, "_memory_prompt_with_comment_context", lambda base_prompt, **kwargs: base_prompt, raising=False)
    monkeypatch.setattr(agent, "_append_system_messages_to_prompt", lambda base_prompt, tid: base_prompt, raising=False)
    monkeypatch.setattr(agent, "_append_stress_level_to_prompt", lambda base_prompt, tid: base_prompt, raising=False)
    monkeypatch.setattr(agent, "_memory_get_author_id_and_username", lambda post_id: (None, None), raising=False)
    monkeypatch.setattr(agent, "_memory_get_thread_root_id", lambda post_id: 99, raising=False)
    monkeypatch.setattr(agent, "_memory_build_conversation_cues", lambda **kwargs: {}, raising=False)
    monkeypatch.setattr(agent, "_memory_format_conversation_cues", lambda cues: "", raising=False)
    monkeypatch.setattr(agent, "_detect_high_affect_signal", lambda **kwargs: {"is_high_affect": False, "confidence": 0.0, "source": "rules", "triggers": {}}, raising=False)
    monkeypatch.setattr(agent, "_memory_format_high_affect_flags", lambda *args, **kwargs: "", raising=False)
    monkeypatch.setattr(agent, "_memory_collect_high_affect_recall", lambda **kwargs: {"items": [], "counts_by_bucket": {}, "has_usable_memories": False, "prompt_block": ""}, raising=False)
    monkeypatch.setattr(agent, "_build_comment_style_options", lambda **kwargs: {"style_names": ["default"], "quick_styles_allowed": True}, raising=False)
    monkeypatch.setattr(agent, "_forum_forced_skip_reason", lambda target_quality: None, raising=False)
    monkeypatch.setattr(agent, "_select_comment_style", lambda *args, **kwargs: {"selected_style": "default"}, raising=False)
    monkeypatch.setattr(agent, "_log_comment_style_selection", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_generated_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_has_recent_identical_comment", lambda *args, **kwargs: False, raising=False)
    monkeypatch.setattr(agent, "_is_thread_duplicate", lambda *args, **kwargs: False, raising=False)
    monkeypatch.setattr(agent, "_apply_stress_reward_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_recent_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_writing_action", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_decision_log", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_memory_after_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_memory_reply_references_recalled_item", lambda *args, **kwargs: (True, ""), raising=False)
    monkeypatch.setattr(agent, "_memory_rewrite_reply_with_callback", lambda *args, **kwargs: "", raising=False)
    monkeypatch.setattr(agent, "_enforce_text_limits", lambda text, **kwargs: (text, {}), raising=False)
    monkeypatch.setattr(agent, "_Agent__update_user_interests", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "new_opinions", lambda *args, **kwargs: None)

    result = agent.comment(post_id=42, tid=3)

    assert result is None
    comment_payload = next(payload for url, payload in payloads if url.endswith("/comment"))
    assert comment_payload["text"] == "I think this policy is wrong."
    assert comment_payload["emotions"] == ["anger"]
    assert "No emotions were found in this annotated sentence." not in comment_payload["text"]


def test_short_emotion_label_snippets_are_rejected(monkeypatch):
    agent = make_content_agent()
    agent.emotions = [
        "admiration",
        "amusement",
        "anger",
        "annoyance",
        "approval",
        "caring",
        "confusion",
        "curiosity",
        "desire",
        "disappointment",
        "disapproval",
        "disgust",
        "embarrassment",
        "excitement",
        "fear",
        "gratitude",
        "grief",
        "joy",
        "love",
        "nervousness",
        "optimism",
        "pride",
        "realization",
        "relief",
        "remorse",
        "sadness",
        "surprise",
        "trust",
    ]

    assert agent._looks_like_emotion_payload("Sadness nostalgia apprehension")
    assert agent._looks_like_emotion_payload("Anger joy fear")


def test_post_payload_keeps_post_text_separate_from_emotion_annotations(monkeypatch):
    agent = make_content_agent()
    agent.annotate_emotions = True
    agent.opinions_enabled = False
    agent._has_usable_llm_config = lambda: True
    agent._Agent__get_interests = lambda tid: (["climate"], [1])

    payloads = []

    class PostAssistant(FakeAssistantAgent):
        def initiate_chat(self, other, message, silent=True, max_round=1):
            if self.name == "Handler":
                self.chat_messages[other] = [
                    {"content": "I think this policy is wrong."},
                    {"content": "No emotions were found in this annotated sentence."},
                ]
            else:
                self.chat_messages[other] = [{"content": "I think this policy is wrong."}]

    monkeypatch.setattr(base_agent_module, "AssistantAgent", PostAssistant)
    monkeypatch.setattr(
        base_agent_module,
        "post",
        lambda url, headers=None, data=None: payloads.append((url, json.loads(data)))
        or SimpleNamespace(_content=b'{"status": "200"}'),
    )
    monkeypatch.setattr(agent, "_Agent__emotion_annotation", lambda text: ["anger"])
    monkeypatch.setattr(agent, "_Agent__clean_text", lambda text: text)
    monkeypatch.setattr(agent, "_memory_prompt_with_post_context", lambda base_prompt, tid: base_prompt)
    monkeypatch.setattr(agent, "_append_system_messages_to_prompt", lambda base_prompt, tid: base_prompt)
    monkeypatch.setattr(agent, "_append_stress_level_to_prompt", lambda base_prompt, tid: base_prompt)
    monkeypatch.setattr(agent, "_memory_after_post", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent, "_record_self_post_opinions", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent, "_Agent__extract_components", lambda text, c_type="hashtags": [], raising=False)
    monkeypatch.setattr(agent, "_memory_get_external_engine", lambda: None, raising=False)
    monkeypatch.setattr(agent, "_memory_get_author_id_and_username", lambda post_id: (None, None), raising=False)
    monkeypatch.setattr(agent, "_memory_get_thread_root_id", lambda post_id: 99, raising=False)
    monkeypatch.setattr(agent, "_memory_build_conversation_cues", lambda **kwargs: {}, raising=False)
    monkeypatch.setattr(agent, "_memory_format_conversation_cues", lambda cues: "", raising=False)
    monkeypatch.setattr(agent, "_detect_high_affect_signal", lambda **kwargs: {"is_high_affect": False, "confidence": 0.0, "source": "rules", "triggers": {}}, raising=False)
    monkeypatch.setattr(agent, "_memory_format_high_affect_flags", lambda *args, **kwargs: "", raising=False)
    monkeypatch.setattr(agent, "_memory_collect_high_affect_recall", lambda **kwargs: {"items": [], "counts_by_bucket": {}, "has_usable_memories": False, "prompt_block": ""}, raising=False)
    monkeypatch.setattr(agent, "_build_comment_style_options", lambda **kwargs: {"style_names": ["default"], "quick_styles_allowed": True}, raising=False)
    monkeypatch.setattr(agent, "_forum_forced_skip_reason", lambda target_quality: None, raising=False)
    monkeypatch.setattr(agent, "_select_comment_style", lambda *args, **kwargs: {"selected_style": "default"}, raising=False)
    monkeypatch.setattr(agent, "_log_comment_style_selection", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_generated_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_has_recent_identical_comment", lambda *args, **kwargs: False, raising=False)
    monkeypatch.setattr(agent, "_is_thread_duplicate", lambda *args, **kwargs: False, raising=False)
    monkeypatch.setattr(agent, "_apply_stress_reward_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_recent_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_record_writing_action", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_decision_log", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_memory_after_comment", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(agent, "_memory_reply_references_recalled_item", lambda *args, **kwargs: (True, ""), raising=False)
    monkeypatch.setattr(agent, "_memory_rewrite_reply_with_callback", lambda *args, **kwargs: "", raising=False)
    monkeypatch.setattr(agent, "_enforce_text_limits", lambda text, **kwargs: (text, {}), raising=False)
    monkeypatch.setattr(agent, "_Agent__update_user_interests", lambda *args, **kwargs: None, raising=False)

    result = agent.post(tid=3)

    assert result is None
    post_payload = next(payload for url, payload in payloads if url.endswith("/post"))
    assert post_payload["tweet"] == "I think this policy is wrong."
    assert post_payload["emotions"] == ["anger"]
    assert "No emotions were found in this annotated sentence." not in post_payload["tweet"]
