# Prompt And Data Files

Besides the main runtime config, `YClient` depends on several auxiliary configuration files.

## `config_files/prompts.json`

File: [`prompts.json`](/Users/rossetti/PycharmProjects/YClient/config_files/prompts.json)

This file contains the prompt templates used to steer the agents and the handler agents created through PyAutoGen.

### Main Prompt Keys

| Key | Purpose |
| --- | --- |
| `agent_roleplay_base` | minimal persona scaffold |
| `agent_roleplay_simple` | short persona used for simple binary decisions |
| `agent_roleplay` | richer persona for general content generation |
| `agent_roleplay_comments_share` | persona used for comments and shares |
| `handler_instructions` | emotion annotation instructions |
| `handler_instructions_topics` | topic extraction instructions |
| `handler_instructions_simple` | generic action dispatcher instructions |
| `handler_post` | original-post generation |
| `handler_news` | news reaction generation |
| `handler_comment_image` | image reaction generation |
| `handler_comment` | threaded reply generation |
| `handler_share` | article-share generation |
| `handler_reactions` | yes/no/neutral reaction decision |
| `handler_follow` | follow/unfollow decision |
| `handler_action` | action choice classifier |
| `handler_cast` | voting-intention decision |
| `page_roleplay` | broadcaster-page persona |
| `handler_share_page` | page-authored news sharing |

### Template Variables

The templates may interpolate values like:

- `self.name`
- `self.age`
- `self.nationality`
- `self.gender`
- `self.leaning`
- `self.education_level`
- `self.language`
- `self.toxicity`
- `interest`
- `article`
- `website`
- `conv`
- `post_text`

Impact:

- stronger directives make the simulation more stable but can reduce behavioral diversity
- shorter prompts reduce latency and token cost
- aggressive style constraints can overpower the persona traits

## Feed Files

### `config_files/rss_feeds.json`

File: [`rss_feeds.json`](/Users/rossetti/PycharmProjects/YClient/config_files/rss_feeds.json)

Used when `YClientWithPages` loads RSS-backed page agents. Each entry typically contains:

- `name`
- `feed_url`
- `category`
- `leaning`

Impact:

- more feeds create more page agents and more externally seeded content
- feed categories influence topical variety
- leaning values can shape ideological framing in prompts and downstream discussion

### `config_files/feed_small.json`

Reduced feed list for cheaper or quicker runs.

### `config_files/paralympics_feeds.json`

Specialized feed profile for event-specific simulations.

## Agent Seed Files

### `config_files/simulation_agents_bsky.json`

Example agent seed file for reloading a saved population rather than generating a new one.

Use with:

```bash
python y_client.py -a config_files/simulation_agents_bsky.json
```

## Graph File

### `config_files/sample_graph.csv`

Optional initial social graph consumed through `-g/--graph`.

Requirements:

- CSV edge list
- node ids should align with the generated initial population

Impact:

- denser graphs make follower-based timeline reading stronger
- sparse graphs produce more cold-start behavior

## Locale File

### `config_files/nationality_locale.json`

Supports nationality/locale mappings used by profile generation and related helper logic.
