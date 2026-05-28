from y_client.classes.base_agent import Agent


def _bare_agent():
    agent = Agent.__new__(Agent)
    agent.user_id = 11
    return agent


def test_append_system_messages_to_prompt_renders_instructions(monkeypatch):
    agent = _bare_agent()
    monkeypatch.setattr(
        agent,
        "_get_active_system_messages",
        lambda tid: [
            {"type": "moderation", "message": "Start with MOD NOTICE."},
            {"type": "policy", "message": "Avoid insults."},
        ],
    )

    rendered = agent._append_system_messages_to_prompt(base_prompt="Base prompt", tid=4)

    assert "Base prompt" in rendered
    assert "Active system messages addressed to you for this round." in rendered
    assert "[moderation] Start with MOD NOTICE." in rendered
    assert "[policy] Avoid insults." in rendered


def test_get_active_system_messages_normalizes_payload(monkeypatch):
    agent = _bare_agent()

    monkeypatch.setattr(
        agent,
        "_post_json_api",
        lambda route, payload: type(
            "Resp",
            (),
            {
                "__dict__": {
                    "_content": b'[{"type":"moderation","message":"Use MOD NOTICE"},{"type":"","message":"  "}]'
                }
            },
        )(),
    )

    messages = agent._get_active_system_messages(5)

    assert messages == [{"type": "moderation", "message": "Use MOD NOTICE"}]


def test_append_system_messages_to_prompt_is_noop_when_no_messages(monkeypatch):
    agent = _bare_agent()
    monkeypatch.setattr(agent, "_get_active_system_messages", lambda tid: [])

    rendered = agent._append_system_messages_to_prompt(base_prompt="Base prompt", tid=4)

    assert rendered == "Base prompt"
