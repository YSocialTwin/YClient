"""Frequency-weighted choice of the single topic of a post."""

import numpy as np


def pick_topic_index(data, rng=None):
    """Return the index of one topic in ``data`` (or ``None`` if empty).

    ``data`` is the list returned by ``/get_user_interests``: each item may
    carry ``count`` (interactions with the topic in the attention window).
    Probability is proportional to ``count + 1``: frequent topics dominate
    (stability) but every candidate keeps a chance (new interests emerge).
    Servers that do not send ``count`` yield a uniform choice.
    """
    if not data:
        return None
    rng = rng or np.random
    weights = np.array(
        [max(float(item.get("count", 0) or 0), 0.0) + 1.0 for item in data]
    )
    return int(rng.choice(len(data), p=weights / weights.sum()))
