"""Client side of the federation (F3.4a, opt-in): which agents may act, and the agent's choice to cross-post.

With the `federation` section of the client configuration absent or `enabled: false` every function here does
nothing: no request, no random draw, the same lists (INV-01).

- filter_pool(agents): the agents that are not active on this platform (dormant or left) do not act and are not
  sampled; the server tells which they are (GET /federation/inactive_users).
- post_fields(): {"crosspost": True} when this agent chose to cross-post the post it is publishing (D-07). The
  choice is a Bernoulli draw with `federation.crosspost_propensity` (default 0 = never) from a generator of its own
  (seeded with `federation.seed`), never the global one."""

from __future__ import annotations

import random

import requests

_state = {"enabled": False, "api": None, "propensity": 0.0, "rng": None, "inactive": set(), "attention": {}}


def install(config):
    """Read config["federation"]; call once when the client starts."""
    section = (config or {}).get("federation") or {}
    enabled = bool(section.get("enabled"))
    _state.update(enabled=enabled, inactive=set(), api=None, propensity=0.0, rng=None, attention={})
    if enabled:
        api = str((config.get("servers") or {}).get("api", "")).rstrip("/")
        _state.update(api=api, propensity=float(section.get("crosspost_propensity", 0.0)),
                      rng=random.Random(section.get("seed", 0)))
    return enabled


def enabled():
    return bool(_state["enabled"])


def inactive_ids():
    """Ids of the accounts that must not act now (the last known list when the server cannot be reached)."""
    if not _state["enabled"]:
        return set()
    try:
        res = requests.get(f"{_state['api']}/federation/inactive_users", timeout=5)
        _state["inactive"] = {int(i) for i in res.json().get("inactive", [])}
    except Exception:  # noqa: BLE001 - keep the last known list
        pass
    return set(_state["inactive"])


def refresh_attention():
    """Read the attention multipliers of the day from the server (the last known ones when it cannot be reached)."""
    if not _state["enabled"]:
        return
    try:
        res = requests.get(f"{_state['api']}/federation/attention", timeout=5)
        _state["attention"] = {int(k): float(v) for k, v in res.json().get("multipliers", {}).items()}
    except Exception:  # noqa: BLE001 - keep the last known multipliers
        pass


def scale_actions(n, user_id):
    """Number of actions of the agent in the slot after the attention multiplier of the federation (F4.3).

    Exactly `n` when the federation is off or the multiplier is 1 (nothing is drawn); otherwise `n * m` rounded at random
    with the generator of this module, so the global one is untouched. A multiplier below 1 can bring it to 0 (the agent
    does not act in the slot), one above 1 never below `n`."""
    m = _state["attention"].get(user_id, 1.0) if _state["enabled"] else 1.0
    if m == 1.0:
        return n
    x = n * m
    whole = int(x)
    k = whole if x == whole else whole + (1 if _state["rng"].random() < x - whole else 0)  # an exact count draws nothing
    return max(n if m > 1.0 else 0, k)


def filter_pool(agents):
    """The agents allowed to act: the same list object when nobody is inactive (or the federation is off)."""
    if not _state["enabled"]:
        return agents
    refresh_attention()
    hidden = inactive_ids()
    if not hidden:
        return agents
    return [a for a in agents if getattr(a, "user_id", None) not in hidden]


def post_fields():
    """Extra fields of the /post payload."""
    if not _state["enabled"] or _state["propensity"] <= 0.0:
        return {}
    return {"crosspost": True} if _state["rng"].random() < _state["propensity"] else {}
