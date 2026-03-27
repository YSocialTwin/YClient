import json
from collections import Counter
from enum import Enum

from requests import post

from y_client.llm import AssistantAgent
from y_client.opinion_dynamics.utils import get_opinion_group


def llm_evaluation(
    uid,
    x,
    y,
    text=None,
    topic=None,
    evaluation_scope="interlocutor_only",
    cold_start="neutral",
    group_classes=None,
    base_url=None,
    llm_config=None,
    **kwargs,
):
    if x is None:
        if cold_start == "neutral":
            x = 0.5
        elif cold_start in ("author", "inherited"):
            x = y

    if x is None or group_classes is None:
        return y

    x_group = get_opinion_group(float(x), group_classes)
    y_group = get_opinion_group(float(y), group_classes)

    peer_groups = []
    if evaluation_scope != "interlocutor_only":
        peer_groups = _get_peer_groups(uid, topic, base_url, group_classes)

    prompt = (
        f"Read the following text on the topic '{str(topic or '').upper()}': '{text}'.\n"
        f"The author has opinion '{y_group}' on the topic.\n"
        f"Your initial opinion is '{x_group}'."
    )
    if peer_groups:
        prompt += " The following are the opinions of your friends:\n"
        for opinion_group, count in peer_groups:
            prompt += f"Opinion: '{opinion_group}' ({count})\n"
    prompt += "\nAnswer with a single word among the options: AGREE|DISAGREE|NEUTRAL."

    response = _llm_eval(llm_config, prompt)
    if "AGREE" in response.upper():
        _, updated_value = shift_class(x_group, y_group, Direction.AGREE, group_classes)
        return updated_value
    if "DISAGREE" in response.upper():
        _, updated_value = shift_class(x_group, y_group, Direction.DISAGREE, group_classes)
        return updated_value
    return float(x)


def _get_peer_groups(user_id, topic=None, base_url=None, group_classes=None):
    api_url = f"{base_url}/get_users_opinions"
    response = post(
        api_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=json.dumps({"user_id": user_id, "topic": topic}),
    )
    values = json.loads(response.__dict__["_content"].decode("utf-8"))
    grouped = [get_opinion_group(float(value), group_classes) for value in values]
    return list(Counter(grouped).items())


def _llm_eval(llm_config, text):
    user_agent = AssistantAgent(
        name="agent",
        llm_config=llm_config,
        system_message="",
        max_consecutive_auto_reply=1,
    )
    return user_agent.generate_reply(messages=[{"role": "user", "content": text}])


class Direction(Enum):
    AGREE = 1
    DISAGREE = -1


def _class_mid(bounds):
    return (bounds[0] + bounds[1]) / 2


def shift_class(current_group, target_group, direction, class_bounds):
    ordered = sorted(class_bounds.items(), key=lambda item: item[1][0])
    labels = [label for label, _ in ordered]
    bounds_map = dict(ordered)

    if current_group not in bounds_map or target_group not in bounds_map:
        raise ValueError("Class label not found")
    if current_group == target_group:
        return current_group, _class_mid(bounds_map[current_group])

    current_idx = labels.index(current_group)
    target_idx = labels.index(target_group)
    step_towards_target = 1 if target_idx > current_idx else -1

    if direction == Direction.AGREE:
        step = step_towards_target
    elif direction == Direction.DISAGREE:
        step = -step_towards_target
    else:
        raise ValueError("Unknown direction")

    new_idx = max(0, min(current_idx + step, len(labels) - 1))
    new_group = labels[new_idx]
    return new_group, _class_mid(bounds_map[new_group])
