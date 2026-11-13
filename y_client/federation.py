"""Client side of the federation (F3.4a, opt-in): which agents may act, and the agent's choice to cross-post.

With the `federation` section of the client configuration absent or `enabled: false` every function here does
nothing: no request, no random draw, the same lists (INV-01).

- filter_pool(agents): the agents that are not active on this platform (dormant or left) do not act and are not
  sampled; the server tells which they are (GET /federation/inactive_users).
- post_fields(): {"crosspost": True} when this agent chose to cross-post the post it is publishing (D-07). The
  choice is a Bernoulli draw with `federation.crosspost_propensity` (default 0 = never) from a generator of its own
  (seeded with `federation.seed`), never the global one."""

from __future__ import annotations

import json
import logging
import random
import re
import threading

import requests

_state = {"enabled": False, "api": None, "propensity": 0.0, "rng": None, "inactive": set(), "attention": {},
          "mode": "coordinator_rule", "member": None, "peers": {}, "label": None, "adopt": False, "decision": "random",
          "triggers": ("publish", "interaction"), "max_per_day": 5, "content": frozenset(), "counts": {}}

# Longest text each destination accepts (characters); the rules and the parser of an LLM reply both apply them.
LIMITS = {"microblogging": 280, "forum": 2000, "photo_sharing": 300, "instant_messaging": 400, "dating": 200}


def _share_blocked(content):
    """crosspost.content (additive, OR): the share of the content of others can be eligible with `all` (or no setting) and
    with `news` or `images` selected; with only `own_content` (alias `own_posts`) it never can."""
    names = {str(c) for c in (content or ())}
    return bool(names) and "all" not in names and not (names & {"news", "images"})


def install(config):
    """Read config["federation"]; call once when the client starts."""
    section = (config or {}).get("federation") or {}
    enabled = bool(section.get("enabled"))
    _state.update(enabled=enabled, inactive=set(), api=None, propensity=0.0, rng=None, attention={},
                  mode="coordinator_rule", member=None, peers={}, label=None, adopt=False, share_blocked=False,
                  decision="random", triggers=("publish", "interaction"), max_per_day=5, content=frozenset(), counts={})
    if enabled:
        api = str((config.get("servers") or {}).get("api", "")).rstrip("/")
        _state.update(api=api, propensity=float(section.get("crosspost_propensity", 0.0)),
                      rng=random.Random(section.get("seed", 0)),
                      mode=str(section.get("crosspost_mode") or "coordinator_rule"), member=section.get("member"), label=section.get("name"),
                      adopt=bool(section.get("adopt")),
                      share_blocked=_share_blocked(section.get("crosspost_content")))
        _state.update(read_decision(section))
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


def adopt_provisioned(client, include_adopted=False):
    """INV-19: accounts the server created because an agent of another platform decided to join this one get an agent here.

    Only with `federation.adopt` in the client configuration. Each account the server lists (GET /federation/provisioned)
    becomes an agent of `client` (`client.adopt_federated_account(account)` returns it, or None) and is reported as adopted;
    the new agent acts like any other from the next slot. Returns the number adopted; never raises for an unreachable server.
    With `include_adopted` (a client that restarts) the accounts adopted before are listed too: the population file does not
    hold them, and without an agent here they would stay silent for the rest of the run."""
    if not (_state["enabled"] and _state["adopt"]):
        return 0
    try:
        url = f"{_state['api']}/federation/provisioned" + ("?all=1" if include_adopted else "")
        res = requests.get(url, timeout=5)
        accounts = res.json().get("accounts", [])
    except Exception:  # noqa: BLE001 - try again at the next slot
        return 0
    done = []
    for account in accounts:
        agent = client.adopt_federated_account(account)
        if agent is not None and getattr(agent, "user_id", None) is not None:
            done.append(int(account["user_id"]))
    if done:
        try:
            requests.post(f"{_state['api']}/federation/provisioned/adopted", json={"user_ids": done}, timeout=5)
        except Exception:  # noqa: BLE001 - they are offered again and skipped as already known
            pass
    return len(done)


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


def agent_action():
    """True when the agent itself chooses where to cross-post and with which text (crosspost.mode = agent_action)."""
    return bool(_state["enabled"]) and _state["mode"] == "agent_action"


def destinations(user_id):
    """Platforms where this agent can post now (the server tells; empty when it cannot be reached)."""
    try:
        res = requests.get(f"{_state['api']}/federation/destinations", params={"user_id": user_id}, timeout=5)
        doc = res.json()
        if doc.get("members"):  # P15: member, platform and name of each destination
            _learn(doc["members"])
            return sorted(str(m["member"]) for m in doc["members"])
        return sorted(str(m) for m in doc.get("destinations", []))
    except Exception:  # noqa: BLE001 - no destination known: no cross-post this time
        return []


def source_platform():
    return _state.get("label") or _state["member"] or "another platform"


def platform_of(dest):
    """Platform type of a destination member (P15: several members may share a type; the member name is then
    `<platform>-<id>`). The server answers it with the destinations; without it the member name is the type (older worlds)."""
    return (_state["peers"].get(str(dest)) or {}).get("platform") or str(dest)


def _learn(items):
    """Remember the platform and the name of each destination the server listed (additive fields `platform`, `name`)."""
    for it in items or ():
        if isinstance(it, dict) and it.get("member") and it.get("platform"):
            _state["peers"][str(it["member"])] = {"platform": str(it["platform"]), "name": str(it.get("name") or it["member"])}


def _destination_line(dest):
    kind = platform_of(dest)
    name = (_state["peers"].get(str(dest)) or {}).get("name")
    if kind == str(dest) and (not name or name == str(dest)):
        return f"- {dest} ({LIMITS.get(kind, 280)})"  # a member named after its type: the line of a single-type world
    return f"- {dest} ({name or dest}, {kind}, {LIMITS.get(kind, 280)})"


def adapt_prompt_key(dest):
    """Prompt-store key that adapts a text for the destination platform (None for a platform without one)."""
    return f"crosspost_adapt_{platform_of(dest)}" if platform_of(dest) in LIMITS else None


def _cut(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    return (cut.rsplit(" ", 1)[0] if " " in cut[-30:] else cut).rstrip(",;:- ")


def rule_text(dest, text):
    """The text for the destination without an LLM: the same words, shaped and cut for the platform."""
    dest = platform_of(dest)
    text = " ".join(str(text or "").split()) if dest != "forum" else str(text or "").strip()
    if dest == "forum" and "\n" not in text:
        title = _cut(re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0], 80)
        return f"{title}\n{text}"[:LIMITS["forum"]]
    return _cut(text, LIMITS.get(dest, 280))


def parse_reply(dest, reply, fallback=None):
    """Clean the reply of a model asked to adapt a text: no reasoning block, fences, labels or quotes; at most the
    platform limit; for a forum a title line then a body. The fallback (default: nothing) when little is left."""
    dest = platform_of(dest)
    text = re.sub(r"<think>.*?</think>", "", str(reply or ""), flags=re.S | re.I)
    text = re.sub(r"^```[a-z]*\n?|```$", "", text.strip(), flags=re.M).strip()
    text = re.sub(r"^(post|caption|message|text|testo|didascalia|messaggio|frase)\s*:\s*", "", text, flags=re.I).strip()
    if len(text) >= 2 and (text[0], text[-1]) in {('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u00ab", "\u00bb")}:
        text = text[1:-1].strip()
    if dest == "forum":
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return fallback
        title = re.sub(r"^(title|titolo)\s*:\s*|^#+\s*", "", lines[0], flags=re.I).strip()
        body = " ".join(re.sub(r"^(body|corpo)\s*:\s*", "", ln, flags=re.I) for ln in lines[1:]).strip()
        if not title:
            return fallback
        return _cut(f"{_cut(title, 120)}\n{body or title}", LIMITS["forum"])
    text = " ".join(text.split())
    if len(text) < 3:
        return fallback
    return _cut(text, LIMITS.get(dest, 280))


def crosspost_targets(user_id, text, adapt=None):
    """[{"member", "text"}]: where this agent decided to post its text. One draw per destination (sorted) with
    `federation.crosspost_propensity`, from the generator of this module; `adapt(dest, text)` is the model's version
    (None or empty: the rule text)."""
    if not agent_action() or _state["propensity"] <= 0.0 or not str(text or "").strip():
        return []
    out = []
    for dest in destinations(user_id):
        if _state["rng"].random() >= _state["propensity"]:
            continue
        version = adapt(dest, text) if adapt is not None else None
        out.append({"member": dest, "text": version or rule_text(dest, text)})
    return out


def _draw_post_fields(user_id, text, adapt):
    """The Bernoulli draw of the cross-post choice (crosspost.decision = random, and the fallback of llm)."""
    if not _state["enabled"] or _state["propensity"] <= 0.0:
        return {}
    if _state["mode"] == "agent_action":
        targets = crosspost_targets(user_id, text, adapt) if user_id is not None else []
        return {"crosspost": True, "crosspost_to": targets} if targets else {}
    return {"crosspost": True} if _state["rng"].random() < _state["propensity"] else {}


def post_fields(user_id=None, text=None, adapt=None, decide_with=None, round_id=None, has_image=False):
    """Extra fields of the /post payload. `user_id`, `text`, `adapt` are used only with crosspost.mode = agent_action.

    With crosspost.decision = llm and `decide_with(trigger, text, destination_lines, context)` (the agent's model; None for a
    rule-based agent) the model decides, trigger `publish`; on any failure the draw below is used."""
    if not _state["enabled"]:
        return {}
    decided = decide(user_id, text, "publish", decide_with, round_id, own=True, has_image=has_image)
    if decided is not None and decided["source"] != "fallback":
        return decision_fields(decided, user_id, text, adapt)
    fields = _draw_post_fields(user_id, text, adapt)
    if decided is not None:
        note_fallback(user_id, "publish", fields, decided["reason"])
    return fields


def share_fields(user_id=None, text=None, adapt=None, decide_with=None, round_id=None, context=None):
    """Extra fields of the /share payload (F8): the agent shares the post of another agent and may choose to share it,
    with its own words, on other platforms. Only with crosspost.mode = agent_action: with the coordinator rule a share
    never leaves the platform and nothing is drawn (so the draws of the other actions are the same as before).

    With crosspost.decision = llm the model decides (trigger `interaction`, the content of the other agent being the
    candidate; `context` is the text shared); on any failure the Bernoulli draw is used."""
    if not agent_action() or user_id is None:
        return {}
    if _state["share_blocked"]:  # crosspost.content selects only own_content: a share can never be eligible, do not offer it
        return {}
    decided = decide(user_id, text, "interaction", decide_with, round_id, own=False, context=context)
    if decided is not None and decided["source"] != "fallback":
        return decision_fields(decided, user_id, text, adapt)
    targets = crosspost_targets(user_id, text, adapt)
    fields = {"crosspost": True, "crosspost_to": targets} if targets else {}
    if decided is not None:
        note_fallback(user_id, "interaction", fields, decided["reason"])
    return fields


# --- P14: the agent decides whether to cross-post (crosspost.decision = llm) --------------------------------------------
# `random` (default) is the Bernoulli draw above, unchanged. With `llm` an LLM agent is asked, ONCE per event, whether to
# cross-post the content it just published (trigger `publish`) or interacted with (trigger `interaction`) and, with
# crosspost.mode = agent_action, towards which platforms. Any failure falls back to the draw, so a run never stalls.
DECISIONS = ("random", "llm")
TRIGGERS = ("publish", "interaction")
DEFAULT_MAX_PER_DAY = 5  # model calls per agent per simulated day (0 = no limit)
DECISION_TIMEOUT = 60.0  # seconds a decision may take before the draw is used instead
ROUNDS_PER_DAY = 24  # World Simulation: simulated clock with hourly slots
URL_RE = re.compile(r"https?://\S+", re.I)
_CONTENT_ALIASES = {"own_posts": "own_content"}
_TRUE = {"true", "yes", "si", "sì", "1"}
_FALSE = {"false", "no", "0"}
log = logging.getLogger("y_client.federation")
_lock = threading.Lock()
_stats = {"llm": 0, "fallback": 0, "skipped": 0, "crossposts_llm": 0}


def decision_stats():
    """Counters of this process: decisions taken by the model, fallbacks to the draw, skipped events and cross-posts the model chose."""
    return dict(_stats)


def _content_options(content):
    names = {_CONTENT_ALIASES.get(str(c), str(c)) for c in (content or ())}
    return frozenset() if (not names or "all" in names) else frozenset(names)


def _eligible(text, own=True, has_image=False):
    """Client-side view of crosspost.content (the coordinator stays the authority): False only when the agent's OWN content
    can certainly not be eligible. The content of others is left to the coordinator (it knows the link and the image)."""
    opts = _state["content"]
    if not opts or not own or "own_content" in opts:
        return True
    return ("news" in opts and bool(URL_RE.search(str(text or "")))) or ("images" in opts and bool(has_image))


def parse_decision(reply, allowed):
    """The decision in a model reply: {"crosspost": bool, "destinations": [allowed names, in the order of `allowed`],
    "text": {destination: cleaned text}}, or None when there is no valid JSON object with a boolean `crosspost`.
    Unknown destinations are ignored; texts are cleaned and cut like an adaptation (`parse_reply`)."""
    raw = re.sub(r"<think>.*?</think>", "", str(reply or ""), flags=re.S | re.I)
    decoder, obj = json.JSONDecoder(), None
    for match in re.finditer(r"\{", raw):
        try:
            found, _ = decoder.raw_decode(raw[match.start():])
        except ValueError:
            continue
        if isinstance(found, dict) and "crosspost" in found:
            obj = found
            break
    if obj is None:
        return None
    flag = obj["crosspost"]
    if isinstance(flag, str):
        flag = True if flag.strip().lower() in _TRUE else False if flag.strip().lower() in _FALSE else None
    if not isinstance(flag, bool):
        return None
    asked = obj.get("destinations")
    asked = [str(d).strip().lower() for d in asked] if isinstance(asked, list) else []
    dests = [d for d in allowed if d in asked]
    texts = obj.get("text") if isinstance(obj.get("text"), dict) else {}
    out = {}
    for dest in dests:
        value = next((v for k, v in texts.items() if str(k).strip().lower() == dest), None)
        cleaned = parse_reply(dest, value) if isinstance(value, str) else None
        if cleaned:
            out[dest] = cleaned
    return {"crosspost": flag, "destinations": dests, "text": out}


def destination_lines(dests):
    """The destinations as lines for the prompt: `- forum (2000)`, the number being the longest text in characters."""
    return "\n".join(_destination_line(d) for d in dests)


def _ask_with_timeout(ask, args, timeout):
    box = {}

    def run():
        try:
            box["reply"] = ask(*args)
        except Exception as exc:  # noqa: BLE001 - reported to the caller
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError(f"no decision within {timeout}s")
    if "error" in box:
        raise box["error"]
    return box.get("reply")


def _note(user_id, trigger, source, crosspost, dests, reason=""):
    """One log line per decision, the record YWeb analytics read: `federation_decision agent=.. trigger=.. source=llm|fallback
    crosspost=0|1 destinations=a,b [reason=..]`. For `fallback` the crosspost value is the outcome of the Bernoulli draw."""
    _stats[source] += 1
    if crosspost and source == "llm":
        _stats["crossposts_llm"] += 1
    log.info("federation_decision agent=%s trigger=%s source=%s crosspost=%d destinations=%s%s", user_id, trigger, source,
             1 if crosspost else 0, ",".join(dests), f" reason={reason}" if reason else "")


def note_fallback(user_id, trigger, fields, reason):
    """Log a decision that fell back to the Bernoulli draw (`fields` are the ones the draw produced) and say why."""
    to = [t["member"] for t in fields.get("crosspost_to", [])]
    _note(user_id, trigger, "fallback", bool(fields.get("crosspost")), to, reason)


def decision_for(trigger):
    """True when this event is decided by the model: crosspost.decision = llm and the trigger is selected."""
    return bool(_state["enabled"]) and _state["decision"] == "llm" and trigger in _state["triggers"]


def _precheck(user_id, text, trigger, own, has_image, dests, round_id, day):
    """What can be said before asking the model: {"source": "skip"} (no destination, content not eligible: nothing to do),
    {"source": "fallback", "reason": "cap"} (the agent used its calls of the day) or None (ask the model)."""
    if not dests or not _eligible(text, own, has_image):
        _stats["skipped"] += 1
        return {"source": "skip", "crosspost": False, "destinations": [], "text": {}}
    cap = int(_state["max_per_day"])
    try:  # the simulated day: given (clients that know it) or derived from the round id (hourly slots)
        which = int(day) if day is not None else (int(round_id) // ROUNDS_PER_DAY if round_id is not None else None)
    except (TypeError, ValueError):
        which = None
    if cap > 0 and which is not None:
        with _lock:
            if _state["counts"].get((user_id, which), 0) >= cap:
                return {"source": "fallback", "reason": "cap"}
            _state["counts"] = {k: v for k, v in _state["counts"].items() if k[1] >= which - 1}  # keep today and yesterday
            _state["counts"][(user_id, which)] = _state["counts"].get((user_id, which), 0) + 1
    return None


def _failed(exc):
    return {"source": "fallback", "reason": "timeout" if isinstance(exc, TimeoutError) else f"error:{type(exc).__name__}"}


def _conclude(user_id, trigger, reply, dests):
    """The decision in the reply of the model (see `decide`); a reply that cannot be read is a fallback."""
    parsed = parse_decision(reply, dests)
    if parsed is None:
        return {"source": "fallback", "reason": "invalid"}
    if _state["mode"] == "agent_action":  # the model chooses the destinations; none valid means no cross-post
        parsed["crosspost"] = bool(parsed["crosspost"] and parsed["destinations"])
    else:  # coordinator_rule: the model only marks the content, the coordinator's probabilities choose where it goes
        parsed["destinations"], parsed["text"] = [], {}
    _note(user_id, trigger, "llm", parsed["crosspost"], parsed["destinations"])
    return dict(parsed, source="llm")


def decide(user_id, text, trigger, ask, round_id=None, own=True, has_image=False, context=None, dests=None, day=None):
    """The model's decision for one event, or None when this event is not decided by a model (random mode, trigger not
    selected, rule-based agent: `ask` is None, nothing to say): the caller keeps the Bernoulli draw as before.

    Otherwise {"source": "skip"} (no destination, content not eligible: no call, nothing to do), {"source": "fallback",
    "reason": ..} (cap reached, timeout, model error, invalid JSON: the caller makes the draw and calls `note_fallback`) or
    {"source": "llm", "crosspost": bool, "destinations": [...], "text": {...}}. At most ONE call to `ask(trigger, text,
    destination_lines, context)` per event and `decision_max_per_day` per agent per day; the Bernoulli generator is not used."""
    if not decision_for(trigger) or ask is None or user_id is None or not str(text or "").strip():
        return None
    dests = destinations(user_id) if dests is None else (dests() if callable(dests) else list(dests))
    early = _precheck(user_id, text, trigger, own, has_image, dests, round_id, day)
    if early is not None:
        return early
    try:
        reply = _ask_with_timeout(ask, (trigger, text, destination_lines(dests), context), DECISION_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - a failing or slow model must not stop the agent
        return _failed(exc)
    return _conclude(user_id, trigger, reply, dests)


def decision_fields(decided, user_id, text, adapt=None):
    """The /post or /share fields for a model decision (`decide` returned source `llm` or `skip`)."""
    if not decided.get("crosspost"):
        return {}
    if _state["mode"] != "agent_action":
        return {"crosspost": True}
    targets = []
    for dest in decided["destinations"]:
        version = decided["text"].get(dest) or (adapt(dest, text) if adapt is not None else None)
        targets.append({"member": dest, "text": version or rule_text(dest, text)})
    return {"crosspost": True, "crosspost_to": targets}


def read_decision(section):
    """The decision settings of a member `federation` section (invalid values are logged and mean the default)."""
    decision = str(section.get("crosspost_decision") or "random")
    if decision not in DECISIONS:
        log.warning("federation: unknown crosspost_decision %r, using 'random'", decision)
        decision = "random"
    asked = section.get("crosspost_decision_triggers")
    triggers = tuple(t for t in TRIGGERS if t in asked) if isinstance(asked, (list, tuple)) else TRIGGERS
    try:
        cap = max(0, int(section.get("crosspost_decision_max_per_day", DEFAULT_MAX_PER_DAY)))
    except (TypeError, ValueError):
        cap = DEFAULT_MAX_PER_DAY
    return {"decision": decision, "triggers": triggers, "max_per_day": cap,
            "content": _content_options(section.get("crosspost_content")), "counts": {}}
