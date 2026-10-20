# YClient

`YClient` is the client-side half of the YSocial microblogging simulator. It creates LLM-backed agents, loads prompt templates and feed data, applies recommender systems, and drives social actions against `YServer`.

## What The Client Does

- builds and persists synthetic user profiles
- generates posts, comments, reactions, follows, shares, news commentary, and optional voting behavior
- manages simulation time, agent churn, and stress/reward-aware churn evaluation
- connects each agent to a content recommender and a follow recommender
- supports reciprocal follow/unfollow decisions, including secondary follows
- optionally injects the shared external memory subsystem provided by the `yclient-memory` pip package

## Main Runtime Entry Points

- [`y_client.py`](../y_client.py)
  - CLI entry point used to start a simulation run
- [`y_client/clients/client_base.py`](../y_client/clients/client_base.py)
  - base client for the Twitter-like simulation
- [`y_client/clients/client_with_pages.py`](../y_client/clients/client_with_pages.py)
  - extends the base client with page agents backed by RSS feeds
- [`y_client/classes/base_agent.py`](../y_client/classes/base_agent.py)
  - core user agent implementation

## Configuration Surface

The client behavior is mostly controlled by files under [`config_files/`](../config_files):

- [`config.json`](../config_files/config.json): default full simulation profile
- [`prompts.json`](../config_files/prompts.json): LLM prompt templates
- [`rss_feeds.json`](../config_files/rss_feeds.json): RSS feed catalog
- [`feed_small.json`](../config_files/feed_small.json): reduced feed set
- [`sample_graph.csv`](../config_files/sample_graph.csv): optional initial social graph

## Running The Client

Typical invocation:

```bash
python y_client.py \
  -c config_files/config.json \
  -f config_files/rss_feeds.json \
  -p config_files/prompts.json \
  -x ReverseChronoFollowersPopularity \
  -y PreferentialAttachment
```

For configuration details, see [Main Config](configuration.md) and [Prompt And Data Files](config_files.md).
For the newer stress/reward and reciprocal-follow behaviors, see [Social Feedback Loop](social-feedback.md).
