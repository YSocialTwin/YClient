import json

from y_client.classes.base_agent import Agent


class _FakeAssistantAgent:
    response_text = "NONE"

    def __init__(self, *args, **kwargs):
        self.chat_messages = {}

    def initiate_chat(self, other, message=None, silent=True, max_round=1):
        other.chat_messages[self] = [{"content": self.response_text}]

    def reset(self):
        return None


def _build_agent():
    agent = Agent.__new__(Agent)
    agent.name = "tester"
    agent.user_id = 11
    agent.base_url = "http://example.test"
    agent.llm_config = {"config_list": [{"model": "llama3.2"}]}
    agent.prompts = {"agent_roleplay_simple": "persona"}
    agent._has_usable_llm_config = lambda: True
    agent._Agent__effify = lambda template, **kwargs: template.format(**kwargs) if kwargs else template
    agent._Agent__get_post = lambda post_id: "offensive content"
    return agent


def test_report_posts_server_payload(monkeypatch):
    agent = _build_agent()
    calls = []

    monkeypatch.setattr("y_client.classes.base_agent.AssistantAgent", _FakeAssistantAgent)
    monkeypatch.setattr(
        "y_client.classes.base_agent.post",
        lambda url, headers=None, data=None: calls.append((url, json.loads(data))),
    )
    _FakeAssistantAgent.response_text = "REPORT_TOXIC"

    report_type = agent.report(post_id=7, tid=9)

    assert report_type == "toxic"
    assert calls[0][0].endswith("/report")
    assert calls[0][1] == {"user_id": 11, "post_id": 7, "type": "toxic", "tid": 9}


def test_select_action_lite_read_never_reports(monkeypatch):
    agent = _build_agent()
    reaction_calls = []
    report_calls = []

    monkeypatch.setattr("y_client.classes.base_agent.random.sample", lambda seq, n: [seq[0]])
    agent.read = lambda: json.dumps([5])
    agent.reaction = lambda post_id, tid, check_follow=True: reaction_calls.append(
        (post_id, tid, check_follow)
    )
    agent.report = lambda post_id, tid: report_calls.append((post_id, tid))

    agent.select_action_lite(tid=4, actions=["READ"])

    assert reaction_calls == [(5, 4, True)]
    assert report_calls == []
