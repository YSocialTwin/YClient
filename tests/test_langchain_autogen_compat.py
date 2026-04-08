from __future__ import annotations

import sys
import types
from y_client.llm.autogen_compat import AssistantAgent, MultimodalConversableAgent
import y_client.llm.autogen_compat as compat_module


def test_assistant_agent_single_reply(monkeypatch):
    calls = []

    def fake_invoke_text_model(*, llm_config, system_prompt, user_prompt):
        calls.append((system_prompt, user_prompt))
        return f"{system_prompt}|{user_prompt}"

    monkeypatch.setattr(compat_module, "_invoke_text_model", fake_invoke_text_model)

    initiator = AssistantAgent(name="handler", system_message="handler", max_consecutive_auto_reply=0)
    peer = AssistantAgent(name="writer", system_message="writer", max_consecutive_auto_reply=1)

    initiator.initiate_chat(peer, message="prompt", max_round=1, silent=True)

    assert initiator.chat_messages[peer] == [{"content": "writer|prompt"}]
    assert peer.chat_messages[initiator] == [{"content": "writer|prompt"}]
    assert initiator.last_message(peer) == {"content": "writer|prompt"}
    assert calls == [("writer", "prompt")]


def test_assistant_agent_two_step_exchange(monkeypatch):
    def fake_invoke_text_model(*, llm_config, system_prompt, user_prompt):
        return f"{system_prompt}>{user_prompt}"

    monkeypatch.setattr(compat_module, "_invoke_text_model", fake_invoke_text_model)

    initiator = AssistantAgent(name="handler", system_message="handler", max_consecutive_auto_reply=1)
    peer = AssistantAgent(name="writer", system_message="writer", max_consecutive_auto_reply=1)

    initiator.initiate_chat(peer, message="prompt", max_round=1, silent=True)

    expected = [
        {"content": "writer>prompt"},
        {"content": "handler>writer>prompt"},
    ]
    assert initiator.chat_messages[peer] == expected
    assert peer.chat_messages[initiator] == expected
    assert initiator.last_message(peer) == expected[-1]


def test_multimodal_agent_wraps_text_response(monkeypatch):
    monkeypatch.setattr(
        compat_module,
        "_invoke_vision_model",
        lambda **kwargs: "vision result",
    )

    user_proxy = AssistantAgent(name="user", max_consecutive_auto_reply=0)
    vision_agent = MultimodalConversableAgent(name="vision", llm_config={})

    user_proxy.initiate_chat(vision_agent, message="Describe <img https://example.test/a.png>", silent=True)

    assert vision_agent.chat_messages[user_proxy] == [{"content": [{"text": "vision result"}]}]


def test_build_chat_model_uses_chatollama_for_ollama_base(monkeypatch):
    fake_module = types.ModuleType("langchain_ollama")

    class FakeChatOllama:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_module.ChatOllama = FakeChatOllama
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)
    monkeypatch.delitem(sys.modules, "langchain_openai", raising=False)

    model = compat_module._build_chat_model(
        {
            "config_list": [
                {
                    "model": "llama3.2",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "EMPTY",
                }
            ],
            "temperature": 0.2,
            "max_tokens": 64,
        }
    )

    assert isinstance(model, FakeChatOllama)
    assert model.kwargs["model"] == "llama3.2"
    assert model.kwargs["base_url"] == "http://127.0.0.1:11434"
    assert model.kwargs["temperature"] == 0.2
    assert model.kwargs["num_predict"] == 64


def test_looks_like_ollama_honors_explicit_backend_hint():
    cfg = compat_module._NormalizedLLMConfig(
        model="gpt-4o-mini",
        base_url="https://example.com/v1",
        api_key="token",
        timeout=None,
        temperature=None,
        max_tokens=None,
        backend_hint="ollama",
    )
    assert compat_module._looks_like_ollama(cfg) is True


def test_looks_like_ollama_honors_env_url_match(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("LLM_URL", "https://llm.example.org/custom/v1")
    cfg = compat_module._NormalizedLLMConfig(
        model="llama3.2",
        base_url="https://llm.example.org/custom/v1",
        api_key="EMPTY",
        timeout=None,
        temperature=None,
        max_tokens=None,
        backend_hint=None,
    )
    assert compat_module._looks_like_ollama(cfg) is True
