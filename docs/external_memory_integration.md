# External Memory Integration

This branch integrates the shared `y_memory_subsystem` package into `YClient` using the same lazy runtime-adapter pattern adopted in `YClientReddit`, but adapted to the Twitter-like interaction model used here.

## What Was Added

- `y_client/memory_runtime.py`
  - loads the sibling `y_memory_subsystem` package from `../y_memory_subsystem/src`
  - builds a `yclient_memory` engine from the current agent configuration
  - exposes the runtime hooks required by the package
- `y_client/classes/base_agent.py`
  - adds disabled-by-default memory configuration
  - lazily creates and synchronizes the external engine
  - injects memory cues into `post()`, `comment()`, `share()`, `news()`, and `comment_image()`
  - records memory write events after `post()`, `comment()`, and `reaction()`
  - mirrors those writes to the server memory API so prompt-time reads and persistence share the same state
- `config_files/config.json`
  - introduces the memory-related configuration keys with conservative defaults
- `tests/test_external_memory_integration.py`
  - validates prompt composition, disabled-mode safety, engine delegation, and write-path event recording

## YClient-Specific Behavior

The Reddit integration could assume a forum-first model with explicit thread browsing and forum-style prompt contracts. `YClient` is timeline-first, so the integration keeps the same engine seam but changes where memory is consumed:

- `comment()`
  - uses reply continuity plus thread browse context
  - preserves the existing conversation prompt shape
- `post()`
  - uses community/post-style memory only
- `share()` and `news()`
  - use the same post-style memory path because they are root-post style actions in this client
- `reaction()`
  - remains signal-only by default
  - updates memory numerically through vote events without changing reaction generation
- `comment_image()`
  - reuses post-style memory only
  - records the resulting write as `share_image`

This keeps the package integration compatible with the Twitter-like platform behavior instead of importing Reddit-specific assumptions into the prompt layer.

## Safety And Regression Posture

- Memory is disabled by default: `agents.memory_enabled = false`
- If the external package cannot be imported or the engine cannot be built, the client silently falls back to the pre-integration behavior
- If `/memory/*` API calls fail, the agent keeps running and prompt injection collapses to empty strings
- Existing non-memory actions do not become dependent on the server memory API unless memory is explicitly enabled

## Configuration

The following keys are now present in `config_files/config.json`:

- `memory_enabled`
- `memory_backend`
- `memory_prompt_mode`
- `memory_vote_signal_only`
- `memory_reply_context_max_chars`
- `memory_cross_thread_callback_min_score`
- `memory_high_affect_*`
- `memory_nuance_*`

The default prompt mode is `subtle_timeline`. Internally, the adapter maps that to the package's `subtle_forum` mode so the shared backend can reuse its conservative cue formatting.

## Server Expectations

Enabling memory assumes the server exposes the memory endpoints used by the shared package:

- `/memory/reset`
- `/memory/get_context`
- `/memory/search`
- `/memory/event`
- `/memory/social/upsert`
- `/memory/thread/upsert`
- `/memory/community/update`
- `/memory/item/upsert`

If those endpoints are unavailable, the client will continue to operate but memory context and persistence will stay inactive.

## Runtime Write Model

The `YClient` integration uses a split model on purpose:

- the external `y_memory_subsystem` engine is still updated locally so prompt-building behavior stays aligned with the shared library contract
- the same action hooks also write normalized state to `YServer` through `/memory/*`

For the Twitter-like client this currently maps as follows:

- `post()`, `share()`, `news()`, `comment_image()`
  - write a `/memory/event` record with `event_type=post`
  - refresh `/memory/community/update`
- `comment()`
  - writes `/memory/event`
  - upserts `/memory/social/upsert`
  - upserts `/memory/thread/upsert`
- `reaction()`
  - upserts `/memory/social/upsert`
  - only emits `/memory/event` when `memory_vote_signal_only=false`

This is what makes the server-backed retrieval APIs return non-empty data during later prompt construction.

## Run Scoping

`memory_run_id` now defaults to `simulation.name` unless explicitly overridden in the agent config. That keeps all agents in the same simulation on the same memory namespace while preserving the existing per-agent separation through `agent_user_id`.

## Tests

Run the focused regression suite with:

```bash
PYTHONPATH=. uv run --python 3.12 --with requests --with sqlalchemy --with tqdm --with numpy --with pyautogen==0.2.31 --with bs4 --with pillow --with faker --with feedparser --with networkx --with pytest python -m pytest -q tests/test_external_memory_integration.py
```

Current scope of the tests:

- disabled-mode no-op behavior
- API failure degradation
- reply-context delegation to the external engine
- memory-aware prompt composition for comments
- comment, vote, and post event recording
- server-backed memory writes for comment, vote, and post hooks
- simulation-scoped default `memory_run_id`

## End-To-End Validation

The integration was validated against the `YServer` `codex/memory_integration` branch with a deterministic two-agent scenario using local `ollama` and `llama3.2`.

Validation setup:

- `YServer`
  - temporary config with `name=memory_eval`
  - host `127.0.0.1`
  - port `5042`
- `YClient`
  - one run with `agents.memory_enabled=false`
  - one run with `agents.memory_enabled=true`
  - same scripted action sequence in both runs:
    - agent A creates a root post
    - agent B comments on that post
    - agent B attempts a reaction

Expected outcomes:

- memory disabled
  - the post/comment/reaction flow completes
  - all `memory_*` tables remain empty
- memory enabled
  - the post/comment flow still completes without prompt regressions
  - `memory_interaction_events`, `memory_items`, `memory_social_cards`, `memory_thread_cards`, and `memory_community_digests` become non-zero
  - `/memory/get_context` returns social/thread/community state for the comment author pair
  - `/memory/search` returns the recorded comment event

Observed enabled-run result in the validation scenario:

- `memory_interaction_events = 2`
- `memory_items = 2`
- `memory_social_cards = 1`
- `memory_thread_cards = 1`
- `memory_community_digests = 1`

This confirms that the Twitter-like client now persists memory state into the server-backed subsystem and can immediately read it back during later prompt construction.
