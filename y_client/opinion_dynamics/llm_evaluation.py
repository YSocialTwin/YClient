from typing import Any
from autogen import AssistantAgent

from y_client.opinion_dynamics.utils import get_opinion_group
from requests import post
from collections import Counter
import json
from enum import Enum


def llm_evaluation(uid: int, x: float, y: float, text: str = None, topic: str = None,
                   evaluation_scope: str = "interlocutor_only", cold_start: str = "neutral", group_classes: dict = None,
                   base_url: str = None, llm_config: dict = None) -> float | str:
    """
    LLM-based evaluation of opinion dynamics between two users.
    :param uid:
    :param x:
    :param y:
    :param text:
    :param topic:
    :param evaluation_scope:
    :param cold_start:
    :param group_classes:
    :param base_url:
    :param llm_config:
    :return:
    """

    if x is None:
        if cold_start == "neutral":
            x = 0.5
        if cold_start == "inherited":
            x = y

    else:
        x_op = get_opinion_group(x, group_classes)
        y_op = get_opinion_group(y, group_classes)

        if evaluation_scope != "interlocutor_only":
            peers_opinions = __get_opinions(uid, topic, base_url, group_classes)

        text = (f"Read the following text on the topic '{topic.upper()}': '{text}'.\n "
                f"The author has opinion '{y_op}' on the topic.\n "
                f"Your initial opinion is '{x_op}'")

        if evaluation_scope != "interlocutor_only":
            text += " The following are the opinions of your friends:\n"
            for op, count in peers_opinions:
                text += (f"Opinion: '{op}' ({count})\n")

        text += (f"\nWhat do you think about the expressed opinion? Answer with a single word among the options: AGREE|DISAGREE|NEUTRAL.\n")

        response = llm_eval(llm_config=llm_config, text=text)

        if "AGREE" in response.upper():
            new_class, x = shift_class(x_op, y_op, Direction.AGREE, group_classes)
        elif "DISAGREE" in response.upper():
            new_class, x = shift_class(x_op, y_op, Direction.AGREE, group_classes)

    return x


def __get_opinions(user_id: int, topic: str | None = None, base_url: str = None, group_classes: dict = None) -> list[
    tuple[Any, int]]:

    api_url = f"{base_url}/get_users_opinions"

    data = {
        "user_id": user_id,
        "topic": topic
    }
    response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data))
    data = json.loads(response.__dict__["_content"].decode("utf-8"))

    opinions = [get_opinion_group(float(x), group_classes) for x in data]
    opinions = list(Counter(opinions).items())

    return opinions


def llm_eval(llm_config, text):
    user_agent = AssistantAgent(
        name="agent",
        llm_config=llm_config,
        system_message="",
        max_consecutive_auto_reply=1,
    )

    post_text = user_agent.generate_reply(messages=[{"role": "user", "content": text}])
    return post_text


class Direction(Enum):
    AGREE = 1
    DISAGREE = -1


def class_mid(bounds):
    return (bounds[0] + bounds[1]) / 2


def shift_class(A, B, direction, class_bounds):
    # Order classes by lower bound
    ordered = sorted(
        class_bounds.items(),
        key=lambda x: x[1][0]
    )

    labels = [lbl for lbl, _ in ordered]
    bounds_map = dict(ordered)

    if A not in bounds_map or B not in bounds_map:
        raise ValueError("Class label not found")

    # Case: identical classes → no shift
    if A == B:
        return A, class_mid(bounds_map[A])

    idx_A = labels.index(A)
    idx_B = labels.index(B)

    # Determine step direction
    step_towards_B = 1 if idx_B > idx_A else -1

    if direction == Direction.AGREE:
        step = step_towards_B
    elif direction == Direction.DISAGREE:
        step = -step_towards_B
    else:
        raise ValueError("Unknown direction")

    new_idx = idx_A + step

    # Clamp to boundaries
    new_idx = max(0, min(new_idx, len(labels) - 1))

    new_label = labels[new_idx]
    new_mid = class_mid(bounds_map[new_label])

    return new_label, new_mid
