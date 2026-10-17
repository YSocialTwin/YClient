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
    assert ps.get("moderation_system", "zz") == ps.get("moderation_system", "en")


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


def test_render_follows_paths_items_joins_and_formats_without_evaluating():
    class Agent:
        age = 30
        _secret = "x"

    out = ps.render(
        "{self.age} {article['title']} {', '.join(tags)} {score:.2f} {\"a\": 1}",
        self=Agent(),
        article={"title": "T"},
        tags=["a", "b"],
        score=0.5,
    )
    assert out == '30 T a, b 0.50 {"a": 1}'
    with pytest.raises(ps.PromptError):
        ps.render("{self._secret}", self=Agent())
    with pytest.raises(ps.PromptError):
        ps.render("{missing.name}")
    assert ps.render("{self.upper()}", self="x") == "{self.upper()}"


def test_other_languages_use_their_file_and_fall_back_per_key(tmp_path, monkeypatch, caplog):
    import json

    en = {"a": "Hello {who}", "b": "Only English"}
    (tmp_path / "prompts_internal.json").write_text(json.dumps(en))
    (tmp_path / "prompts_internal.xx.json").write_text(json.dumps({"a": "Ciao {who}"}))
    monkeypatch.setattr(ps, "PACK_FILE", tmp_path / "prompts_internal.json")
    monkeypatch.setattr(ps, "_cache", {})
    monkeypatch.setattr(ps, "_warned", set())
    assert ps.prompt("a", "xx", who="Ann") == "Ciao Ann"
    with caplog.at_level("WARNING"):
        assert ps.get("b", "xx") == "Only English"
        assert ps.get("b", "xx") == "Only English"
    assert len([r for r in caplog.records if "no 'xx' text" in r.getMessage()]) == 1
    assert ps.get("a", "yy") == "Hello {who}"  # language without a file
    assert ps.get("a", "../etc") == "Hello {who}"  # never used as a path
    ps.set_language("xx")
    try:
        assert ps.prompt("a", who="Ann") == "Ciao Ann"
    finally:
        ps.set_language("en")


def test_italian_pack_is_complete_and_translated():
    import json
    import pathlib

    here = pathlib.Path(ps.__file__).parent
    en = json.loads((here / "prompts_internal.json").read_text(encoding="utf-8"))
    it = json.loads((here / "prompts_internal.it.json").read_text(encoding="utf-8"))
    assert set(en) == set(it)
    assert sum(1 for k in en if en[k] != it[k]) >= len(en) * 0.8
    # English is the default and is never altered by the presence of other packs
    assert ps.get(next(iter(en)), "en") == en[next(iter(en))]


@pytest.fixture
def clean_language(monkeypatch):
    for name in (ps.ENV_VAR, ps.FOLDER_VAR):  # set then delete, so the original (absent) state is restored
        monkeypatch.setenv(name, "x")
        monkeypatch.delenv(name)
    monkeypatch.setattr(ps, "_language", None)
    monkeypatch.setattr(ps, "_values", {})
    yield
    monkeypatch.undo()


def _run_folder(tmp_path, experiment="it", clients=None):
    import json

    (tmp_path / "prompt_language.json").write_text(
        json.dumps({"experiment": experiment, "clients": clients or {}}), encoding="utf-8"
    )
    (tmp_path / "profile_values.it.json").write_text(
        json.dumps({"nationality": {"American": "statunitense"}, "gender": {"male": "uomo"}, "leaning": {"centrist": "centrista"}}),
        encoding="utf-8",
    )
    return tmp_path


def test_language_is_english_unless_a_folder_or_the_environment_says_otherwise(clean_language, tmp_path):
    assert ps.current_language() == "en"
    assert ps.language_from_folder(tmp_path) == "en"
    folder = _run_folder(tmp_path, "it", {"c2": "en"})
    assert ps.language_from_folder(folder) == "it"
    assert ps.language_from_folder(folder, "c2") == "en"
    assert ps.language_from_folder(folder, "other") == "it"


def test_set_language_reaches_other_copies_through_the_environment(clean_language, monkeypatch):
    import os

    ps.set_language("it")
    assert os.environ[ps.ENV_VAR] == "it"
    monkeypatch.setattr(ps, "_language", None)  # a copy of the module that was never told
    assert ps.current_language() == "it"


def test_environment_language_wins_over_the_record(clean_language, tmp_path, monkeypatch):
    folder = _run_folder(tmp_path, "it")
    monkeypatch.setenv(ps.ENV_VAR, "en")
    assert ps.use_language_from_folder(folder) == "en"
    assert ps.localize(object()) is not None


def test_profile_values_read_in_the_prompt_language_without_touching_the_agent(clean_language, tmp_path):
    class Agent:
        nationality = "American"
        gender = "male"
        leaning = "centrist"
        profession = "Astronaut"  # no translation: stays as it is
        age = 31

    agent = Agent()
    assert ps.localize(agent) is agent  # English: the object itself
    assert ps.use_language_from_folder(_run_folder(tmp_path, "it")) == "it"
    view = ps.localize(agent)
    assert (view.nationality, view.gender, view.leaning) == ("statunitense", "uomo", "centrista")
    assert (view.profession, view.age) == ("Astronaut", 31)
    assert agent.nationality == "American"
    text = ps.render("{self.gender} {self.nationality}, {self.age}", self=view)
    assert text == "uomo statunitense, 31"
    attrs = {"nationality": "American", "political_leaning": "centrist", "name": "Ann"}
    assert ps.localize_attrs(attrs) == {"nationality": "statunitense", "political_leaning": "centrista", "name": "Ann"}
    assert attrs["nationality"] == "American"
    assert ps.env_for_workers()[ps.ENV_VAR] == "it"


def test_english_runs_pass_nothing_to_workers(clean_language, tmp_path):
    ps.use_language_from_folder(_run_folder(tmp_path, "en"))
    assert ps.env_for_workers() == {}
