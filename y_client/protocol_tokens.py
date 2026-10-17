"""Protocol tokens: the words the simulator and the language model agree on.

Prompts may be written in any language, but the answers the code reads are always these English words (action
names, YES/NO, opinion labels, ...). They are defined once here and never translated; prompts in other
languages must ask the model to answer with exactly these words.

``has_token`` and ``first_token`` read an answer tolerantly: case, punctuation and surrounding words are
ignored, so ``"Comment."`` and ``"COMMENT!"`` both count as COMMENT, while ``COMMENTS`` does not.

This file is copied unchanged into every repository that reads model answers; keep the copies identical.
"""

import re

# Actions an agent can choose.
POST = "POST"
COMMENT = "COMMENT"
READ = "READ"
SEARCH = "SEARCH"
FOLLOW = "FOLLOW"
SHARE = "SHARE"
IMAGE = "IMAGE"
CAST = "CAST"
NONE = "NONE"
SHARE_LINK = "SHARE_LINK"
SHARE_IMAGE = "SHARE_IMAGE"

# Answers to yes/no and vote questions.
YES = "YES"
NO = "NO"
LEFT = "LEFT"
RIGHT = "RIGHT"

# Opinion evaluation.
AGREE = "AGREE"
DISAGREE = "DISAGREE"
NEUTRAL = "NEUTRAL"

ACTIONS = (POST, COMMENT, READ, SEARCH, FOLLOW, SHARE, IMAGE, CAST, NONE, SHARE_LINK, SHARE_IMAGE)
YES_NO = (YES, NO)
VOTES = (LEFT, RIGHT, NONE)
OPINIONS = (AGREE, DISAGREE, NEUTRAL)

_WORD = re.compile(r"[A-Za-z_]+")


def words(answer):
    """The upper-case words of an answer (letters and underscores only)."""
    return [w.upper() for w in _WORD.findall(answer if isinstance(answer, str) else "")]


def has_token(answer, token):
    """True when ``token`` appears in ``answer`` as a whole word, whatever the case or punctuation."""
    return token in words(answer)


def first_token(answer, allowed):
    """The first word of ``answer`` that is in ``allowed``, or ``None``."""
    for word in words(answer):
        if word in allowed:
            return word
    return None
