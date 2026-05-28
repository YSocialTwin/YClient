# Architecture

## Execution Flow

1. [`y_client.py`](/Users/rossetti/PycharmProjects/YClient/y_client.py) loads the JSON config, prompts, optional existing agents, and optional graph.
2. It instantiates a client class named by `simulation.client`.
3. The client creates or reloads agents and attaches the selected recommender systems.
4. During each slot, agents choose actions based on `simulation.actions_likelihood`.
5. Each action is executed against `YServer` through HTTP endpoints.
6. If memory is enabled, the agent also talks to the shared memory adapter and the `/memory/*` server endpoints.

## Client Variants

### `YClientBase`

Implemented in [`client_base.py`](/Users/rossetti/PycharmProjects/YClient/y_client/clients/client_base.py).

Use this when you want a pure user-agent microblogging simulation with no broadcaster pages.

### `YClientWithPages`

Implemented in [`client_with_pages.py`](/Users/rossetti/PycharmProjects/YClient/y_client/clients/client_with_pages.py).

Additional behavior:

- loads RSS feeds
- creates page agents for those feeds
- injects page-originated posts into the timeline

This is the default in [`config.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config.json).

## Agent Responsibilities

The main agent class is [`base_agent.py`](/Users/rossetti/PycharmProjects/YClient/y_client/classes/base_agent.py).

It owns:

- profile loading and registration
- prompt filling
- interaction generation
- interest updates
- follow/unfollow decisions
- optional memory read/write hooks

## Recommender Systems

The client expects two recommender implementations:

- content recommender via `-x/--crecsys`
- follow recommender via `-y/--frecsys`

These are loaded dynamically from [`y_client/recsys/`](/Users/rossetti/PycharmProjects/YClient/y_client/recsys).

## Data Persistence

- agent metadata can be written to the file selected by `agents_output`
- simulation state and social state live in `YServer`
- RSS/news metadata lives in the client-side local SQLite setup used by the news feed helpers

## Memory Path

When `agents.memory_enabled` is `true`:

- prompt-time reads use the external `yclient-memory` adapter
- state writes are mirrored to `YServer` through `/memory/event`, `/memory/social/upsert`, `/memory/thread/upsert`, and `/memory/community/update`
- the default `memory_run_id` is the configured `simulation.name`
