"""Frequency-weighted choice of the single topic of a post."""

import numpy as np


def pick_topic_index(data, rng=None):
    """Return the index of one topic in ``data`` (or ``None`` if empty).

    ``data`` is the list returned by ``/get_user_interests``: the topics the
    user interacted with in the moving attention window, each with ``count``
    (> 0). The probability is proportional to ``count``; topics without any
    interaction in the window are never considered. Servers that do not send
    ``count`` yield a uniform choice.
    """
    if not data:
        return None
    rng = rng or np.random
    if all("count" not in item for item in data):
        return int(rng.choice(len(data)))
    weights = np.array([max(float(item.get("count") or 0), 0.0) for item in data])
    if weights.sum() <= 0:
        return None
    return int(rng.choice(len(data), p=weights / weights.sum()))
