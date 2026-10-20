"""Protocol tokens are defined once and answers are read tolerantly."""

import re
from pathlib import Path

from y_client import protocol_tokens as pt


def test_answers_are_read_ignoring_case_and_punctuation():
    assert pt.has_token("Comment.", pt.COMMENT)
    assert pt.has_token("COMMENT!", pt.COMMENT)
    assert pt.has_token("I think: neutral, honestly", pt.NEUTRAL)
    assert not pt.has_token("COMMENTS", pt.COMMENT)
    assert not pt.has_token(None, pt.YES)


def test_first_token_follows_the_order_of_the_answer():
    assert pt.first_token("maybe no, but YES", pt.YES_NO) == pt.NO
    assert pt.first_token("something else", pt.YES_NO) is None


def test_tokens_are_upper_case_words_and_listed_once():
    for group in (pt.ACTIONS, pt.YES_NO, pt.VOTES, pt.OPINIONS):
        assert len(set(group)) == len(group)
        assert all(re.fullmatch(r"[A-Z_]+", token) for token in group)


def test_answer_words_are_not_compared_with_split_in_the_code():
    offenders = []
    for path in Path(pt.__file__).parent.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"[\"'][A-Z_]+[\"'] in \w+\.split\(\)", line):
                offenders.append(f"{path.name}:{number}")
    assert not offenders, offenders


def test_disagree_is_not_read_as_agree():

    assert not pt.has_token("DISAGREE", pt.AGREE)
    assert pt.has_token("I disagree? DISAGREE.", pt.DISAGREE)
