"""Prompts moved out of the code (step 1 of the multilingual prompts task) render exactly as the code wrote them."""

import pytest

from y_client import prompt_store as ps


def test_render_replaces_only_named_fields_and_keeps_other_braces():
    text = 'Answer as {"tone": "x"} for {name}.'
    assert ps.render(text, name="Ann") == 'Answer as {"tone": "x"} for Ann.'


def test_render_raises_when_a_named_field_is_missing_and_ignores_extras():
    with pytest.raises(ps.PromptError):
        ps.render("Hi {who}")
    assert ps.render("Hi", who="x") == "Hi"


def test_unknown_key_raises_and_other_languages_fall_back_to_english():
    with pytest.raises(ps.PromptError):
        ps.get("no_such_key")
    assert ps.get("moderation_system", "it") == ps.get("moderation_system", "en")


def test_values_are_rendered_like_an_f_string():
    assert ps.prompt("stress_level_block", label="none", level=1) == (
        "Current stress level: "
        f"{'none'} ({1}/5 on a five-point scale where 1 means none and 5 means extremely stressed). "
        "Use this only as internal emotional context while writing."
    )


def test_stress_annotation_user_matches_the_old_f_string():
    text, user_id, target = "hello", 7, None
    old = (
        "Annotate the interaction for stress/reward scoring.\n"
        f"Actor user id: {user_id}\n"
        f"Recipient user id: {target if target is not None else ''}\n"
        f"Text:\n{text}\n"
        "Return JSON only."
    )
    new = ps.prompt(
        "stress_annotation_user",
        actor_id=user_id,
        recipient_id=target if target is not None else "",
        text=text,
    )
    assert new == old


def test_system_messages_block_matches_the_old_text():
    item = {"type": "warning", "message": "be kind"}
    old = [
        "Active system messages addressed to you for this round.",
        "These are mandatory platform or moderator instructions for the content you are about to write. Follow them exactly.",
        f"- [{item['type']}] {item['message']}",
    ]
    new = [
        ps.get("system_messages_header"),
        ps.get("system_messages_intro"),
        ps.prompt("system_message_item", type=item["type"], message=item["message"]),
    ]
    assert new == old


def test_stress_labels_match():
    assert [
        ps.get(k)
        for k in (
            "stress_level_none",
            "stress_level_slight",
            "stress_level_moderate",
            "stress_level_high",
            "stress_level_extreme",
        )
    ] == [
        "none",
        "slightly stressed",
        "moderately stressed",
        "very stressed",
        "extremely stressed",
    ]


def test_opinion_topics_match_the_old_concatenation():
    sentiment = [{"topic": "tax", "sentiment": "negative"}, {"topic": "war", "sentiment": "neutral"}]
    old = "Your opinion topics of the post you are responding to are: "
    for s in sentiment:
        old += f"{s['topic']}: {s['sentiment']} "
    new = ps.get("opinion_topics_intro")
    for s in sentiment:
        new += ps.prompt("opinion_topic_item", topic=s["topic"], sentiment=s["sentiment"])
    assert new == old


def test_moderation_prompts_match():
    post_text = "some post"
    assert ps.get("moderation_system") == (
        "Read the content and decide whether it should be reported for moderation. "
        "Reply with exactly one label: REPORT_TOXIC, REPORT_OFFENSIVE, or NONE."
    )
    assert ps.prompt("moderation_user", post_text=post_text) == (
        "Classify the following content for moderation. "
        "Use REPORT_TOXIC for hateful, threatening, abusive, or toxic content. "
        "Use REPORT_OFFENSIVE for insulting, vulgar, or norm-breaking content that "
        "is offensive but not necessarily toxic. Use NONE otherwise.\n\n"
        f"##TEXT START##\n{post_text}\n##TEXT END##"
    )


@pytest.mark.parametrize("action", ["follow", "unfollow"])
def test_follow_back_prompt_matches(action):
    source_summary = "username=bob, age=30"
    requested = "follow them back" if action == "follow" else "unfollow them back"
    old = (
        "Another user has just "
        f"{'followed' if action == 'follow' else 'unfollowed'} you.\n\n"
        f"Their profile:\n{source_summary}\n\n"
        f"Decide whether you want to {requested}. "
        "Reply with ONLY YES or NO."
    )
    new_requested = ps.get(
        "follow_back_request_follow" if action == "follow" else "follow_back_request_unfollow"
    )
    new = ps.prompt(
        "follow_back_user",
        verb=ps.get("follow_back_verb_follow" if action == "follow" else "follow_back_verb_unfollow"),
        profile=source_summary,
        requested=new_requested,
    )
    assert new == old


def test_emotion_annotation_matches():
    text_to_annotate = "I am so happy"
    old = (
        f"Annotate the following text with the emotions it elicits:\n\n"
        f"{text_to_annotate}. Answer with a JSON formatted list of emotions only."
    )
    assert ps.prompt("emotion_annotation_user", text=text_to_annotate) == old


def test_image_description_keeps_its_odd_whitespace():
    image = "http://x/y.png"
    old = f"""Describe the following image. 
            Write in english. <img {image}>"""
    assert ps.prompt("image_description_user", image=image) == old


def test_opinion_evaluation_prompt_matches():
    topic, text, y_group, x_group = "tax", "a text", "A", "B"
    peer_groups = [("A", 2), ("C", 1)]
    old = (
        f"Read the following text on the topic '{str(topic or '').upper()}': '{text}'.\n"
        f"The author has opinion '{y_group}' on the topic.\n"
        f"Your initial opinion is '{x_group}'."
    )
    old += " The following are the opinions of your friends:\n"
    for opinion_group, count in peer_groups:
        old += f"Opinion: '{opinion_group}' ({count})\n"
    old += "\nAnswer with a single word among the options: AGREE|DISAGREE|NEUTRAL."

    new = ps.prompt(
        "opinion_eval_context", topic=str(topic or "").upper(), text=text, y_group=y_group, x_group=x_group
    )
    new += ps.get("opinion_eval_peers_intro")
    for opinion_group, count in peer_groups:
        new += ps.prompt("opinion_eval_peer_item", group=opinion_group, count=count)
    new += ps.get("opinion_eval_question")
    assert new == old
