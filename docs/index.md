# YClient

`YClient` is the client-side half of the YSocial microblogging simulator. It creates LLM-backed agents, loads prompt templates and feed data, applies recommender systems, and drives social actions against `YServer`.

## What The Client Does

- builds and persists synthetic user profiles
- generates posts, comments, reactions, follows, shares, news commentary, and optional voting behavior
- manages simulation time and agent churn
- connects each agent to a content recommender and a follow recommender
- optionally injects the shared external memory subsystem implemented in `y_memory_subsystem`

## Main Runtime Entry Points

- [`y_client.py`](/Users/rossetti/PycharmProjects/YClient/y_client.py)
  - CLI entry point used to start a simulation run
- [`y_client/clients/client_base.py`](/Users/rossetti/PycharmProjects/YClient/y_client/clients/client_base.py)
  - base client for the Twitter-like simulation
- [`y_client/clients/client_with_pages.py`](/Users/rossetti/PycharmProjects/YClient/y_client/clients/client_with_pages.py)
  - extends the base client with page agents backed by RSS feeds
- [`y_client/classes/base_agent.py`](/Users/rossetti/PycharmProjects/YClient/y_client/classes/base_agent.py)
  - core user agent implementation

## Configuration Surface

The client behavior is mostly controlled by files under [`config_files/`](/Users/rossetti/PycharmProjects/YClient/config_files):

- [`config.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config.json): default full simulation profile
- [`config_small.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_small.json): smaller-scale scenario
- [`config_test.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_test.json): testing-focused config
- [`prompts.json`](/Users/rossetti/PycharmProjects/YClient/config_files/prompts.json): LLM prompt templates
- [`rss_feeds.json`](/Users/rossetti/PycharmProjects/YClient/config_files/rss_feeds.json): RSS feed catalog
- [`feed_small.json`](/Users/rossetti/PycharmProjects/YClient/config_files/feed_small.json): reduced feed set
- [`sample_graph.csv`](/Users/rossetti/PycharmProjects/YClient/config_files/sample_graph.csv): optional initial social graph

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

For configuration details, see [Main Config](/Users/rossetti/PycharmProjects/YClient/docs/configuration.md) and [Prompt And Data Files](/Users/rossetti/PycharmProjects/YClient/docs/config_files.md).
