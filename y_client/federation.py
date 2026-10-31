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

_state = {"enabled": False, "api": None, "propensity": 0.0, "rng": None, "inactive": set()}


def install(config):
    """Read config["federation"]; call once when the client starts."""
    section = (config or {}).get("federation") or {}
    enabled = bool(section.get("enabled"))
    _state.update(enabled=enabled, inactive=set(), api=None, propensity=0.0, rng=None)
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


def filter_pool(agents):
    """The agents allowed to act: the same list object when nobody is inactive (or the federation is off)."""
    if not _state["enabled"]:
        return agents
    hidden = inactive_ids()
    if not hidden:
        return agents
    return [a for a in agents if getattr(a, "user_id", None) not in hidden]


def post_fields():
    """Extra fields of the /post payload."""
    if not _state["enabled"] or _state["propensity"] <= 0.0:
        return {}
    return {"crosspost": True} if _state["rng"].random() < _state["propensity"] else {}
