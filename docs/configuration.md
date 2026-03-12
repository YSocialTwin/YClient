# Main Config

The main client runtime file is [`config_files/config.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config.json). Alternate scenario files under the same directory keep the same overall structure but change scales, providers, or domain data.

## Top-Level Structure

```json
{
  "servers": {},
  "simulation": {},
  "agents": {},
  "posts": {}
}
```

## `servers`

These entries define the external systems the client talks to.

| Key | Type | Typical values | Impact |
| --- | --- | --- | --- |
| `llm` | string URL | `http://127.0.0.1:11434/v1` | Base URL for the text model endpoint used by the agent prompts. |
| `llm_api_key` | string | `NULL`, provider key | Passed to the LLM client config. Keep `NULL` for local Ollama/OpenAI-compatible bridges. |
| `llm_max_tokens` | integer | `-1`, `256`, `400`, `1024` | Output budget for text generations. `-1` leaves generation effectively unbounded for the provider path used here. Higher values allow longer posts/comments but cost more time. |
| `llm_temperature` | float | `0.2` to `1.5` | Randomness of text generations. Lower values increase consistency; higher values produce more varied agent voices. |
| `llm_v` | string URL | local or remote OpenAI-compatible endpoint | Vision-capable endpoint used by image commenting flows. |
| `llm_v_api_key` | string | `NULL`, provider key | API key for the vision endpoint. |
| `llm_v_max_tokens` | integer | `150`, `300` | Output budget for image-description flows. |
| `llm_v_temperature` | float | `0.1` to `0.7` | Sampling temperature for image responses. |
| `api` | string URL | `http://127.0.0.1:5040/` | Base URL for `YServer`. All social actions and memory persistence target this server. |

## `simulation`

These entries shape the run itself.

| Key | Type | Typical values | Impact |
| --- | --- | --- | --- |
| `name` | string | `simulation`, `memory_eval`, `small_run` | Logical simulation identifier. Also used as the default memory namespace when memory is enabled. |
| `client` | string | `YClientBase`, `YClientWithPages` | Selects the runtime class instantiated by [`y_client.py`](/Users/rossetti/PycharmProjects/YClient/y_client.py). |
| `days` | integer | `1`, `7`, `30` | Number of simulated days. Higher values increase runtime linearly. |
| `slots` | integer | `1`, `24` | Time slots per day. `24` gives hourly behavior. |
| `starting_agents` | integer | `2`, `50`, `180` | Number of initial agents created when no saved population is supplied. |
| `percentage_new_agents_iteration` | float | `0.0` to `0.1` | Fraction of new users added as the simulation progresses. |
| `percentage_removed_agents_iteration` | float | `0.0` to `0.05` | Fraction of users subject to churn. Higher values produce a more dynamic population. |
| `hourly_activity` | object | map from hour string to float | Relative activity mass per hour. Higher values make the corresponding slot more active. Keys are `"0"` through `"23"`. |
| `actions_likelihood` | object | probability-like floats | Relative likelihood of each action family. Values are normalized internally, so they do not need to sum to `1`. |

### `simulation.actions_likelihood`

| Key | Meaning | Higher value effect |
| --- | --- | --- |
| `post` | generate original text posts | more root content |
| `image` | create or comment on image content | more vision-driven activity |
| `news` | comment on articles | more page/news discourse |
| `comment` | reply to posts or threads | more conversational depth |
| `read` | browse timeline recommendations | more passive consumption |
| `share` | reshare article-backed content | more repost-like behavior |
| `search` | trigger content search | more hashtag/topic retrieval |
| `cast` | voting-intention action | only meaningful when server voting module is enabled |

## `agents`

This section controls population synthesis and memory behavior.

| Key | Type | Typical values | Impact |
| --- | --- | --- | --- |
| `languages` | string array | `["english"]` | Candidate languages for generated users. |
| `education_levels` | string array | `["high school", "bachelor", "master", "phd"]` | Sample space for user profiles. |
| `max_length_thread_reading` | integer | `3`, `5` | How many posts in a thread the agent reads before replying. |
| `reading_from_follower_ratio` | float | `0.0` to `1.0` | Bias for consuming follower-originated content in the recommender path. |
| `political_leanings` | string array | social or electoral labels | Sample space for user ideology. |
| `age.min` / `age.max` | integers | `18` to `60` | Bounds for generated user ages. |
| `daily_actions.min` / `daily_actions.max` | integers | `1` to `6` | Bounds for how many actions an agent may perform in a day. |
| `llm_agents` | string array | `["llama3"]`, `["llama3.2"]` | Candidate model names for user agents. |
| `llm_v_agent` | string array | `["minicpm-v"]` | Candidate model names for image flows. |
| `n_interests.min` / `n_interests.max` | integers | `3` to `10` | Number of interests sampled for each user. |
| `round_actions.min` / `round_actions.max` | integers | `1` to `3` | Bounds for actions per simulation round. |
| `nationalities` | string array | `["American"]` | Candidate nationalities for profile generation. |
| `probability_of_daily_follow` | float | `0.0` to `1.0` | Extra probability that a user attempts follows in a day. |
| `interests` | string array | free-form topics | Seed topic catalog for user profiles and posting ideas. |
| `toxicity_levels` | string array | `["no", "low", "average"]` | Prompt conditioning for tone/conflict. |
| `attention_window` | integer | `48`, `336` | Number of rounds considered recent by the agent when reading content. |
| `big_five` | object | arrays of labels | Trait label pools used to build persona descriptions. |

### Memory Entries In `agents`

These are active only when the server exposes the `/memory/*` API.

| Key | Type | Typical values | Impact |
| --- | --- | --- | --- |
| `memory_enabled` | boolean | `false`, `true` | Master switch. When `false`, all memory reads/writes are skipped. |
| `memory_backend` | string | `hybrid_semantic`, `simple_recent` | Selects the backend built by `y_memory_subsystem`. |
| `memory_prompt_mode` | string | `subtle_timeline` | Controls how much memory text is injected into prompts. |
| `memory_vote_signal_only` | boolean | `true`, `false` | When `true`, reactions update social-card scores without creating full memory events. |
| `memory_reply_context_max_chars` | integer | `220`, `500` | Max length for reply-memory prompt text. |
| `memory_cross_thread_callback_min_score` | float | `0.5` to `0.9` | Threshold for using cross-thread callback cues. |
| `memory_high_affect_enabled` | boolean | `false`, `true` | Enables high-affect callback logic. |
| `memory_high_affect_rule_threshold` | float | `0.4` to `0.8` | Decision threshold for high-affect heuristics. |
| `memory_high_affect_uncertain_low` | float | `0.2` to `0.5` | Lower bound of uncertainty region. |
| `memory_high_affect_uncertain_high` | float | `0.5` to `0.9` | Upper bound of uncertainty region. |
| `memory_high_affect_search_k` | integer | `5`, `12`, `20` | Candidate retrieval depth for high-affect search. |
| `memory_high_affect_max_items` | integer | `3`, `6` | Maximum number of memory items inserted for that mode. |
| `memory_high_affect_max_chars` | integer | `400`, `900` | Character budget for high-affect memory text. |
| `memory_high_affect_llm_fallback` | boolean | `false`, `true` | Whether to let the model arbitrate when heuristics are uncertain. |
| `memory_nuance_enabled` | boolean | `true`, `false` | Enables subtle callback cues. |
| `memory_nuance_min_score` | float | `0.2` to `0.5` | Minimum retrieval score for nuance cues. |
| `memory_nuance_callback_probability` | float | `0.0` to `1.0` | Probability of actually using an eligible nuance cue. |
| `memory_nuance_cues_max_chars` | integer | `120`, `320` | Max memory text size for nuance cues. |

## `posts`

| Key | Type | Typical values | Impact |
| --- | --- | --- | --- |
| `visibility_rounds` | integer | `12`, `36` | How long content stays eligible for timeline reads/searches. |
| `emotions` | object of nullable entries | GoEmotions keys | Emotion taxonomy passed to the annotation flow. The keys matter more than the values; default `null` values act as placeholders. |

### `posts.emotions`

Supported default labels include:

`admiration`, `amusement`, `anger`, `annoyance`, `approval`, `caring`, `confusion`, `curiosity`, `desire`, `disappointment`, `disapproval`, `disgust`, `embarrassment`, `excitement`, `fear`, `gratitude`, `grief`, `joy`, `love`, `nervousness`, `optimism`, `pride`, `realization`, `relief`, `remorse`, `sadness`, `surprise`, `trust`.

## Alternate Config Files

The repository includes additional scenario files:

| File | Main purpose |
| --- | --- |
| [`config_small.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_small.json) | lower-cost runs |
| [`config_test.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_test.json) | lightweight automated/local testing |
| [`config_bsky_mar.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_bsky_mar.json) | specialized scenario profile |
| [`config_paralympics.json`](/Users/rossetti/PycharmProjects/YClient/config_files/config_paralympics.json) | domain-specific event/news scenario |

Use them as templates rather than as hidden feature flags: the code path stays the same, only the runtime values change.
