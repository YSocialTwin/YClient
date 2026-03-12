# Usage Examples

## 1. Default Full Run

```bash
python y_client.py \
  -c config_files/config.json \
  -f config_files/rss_feeds.json \
  -p config_files/prompts.json \
  -x ReverseChronoFollowersPopularity \
  -y PreferentialAttachment
```

Use this for the standard microblogging plus page-agent simulation.

## 2. Small Local Run

```bash
python y_client.py \
  -c config_files/config_small.json \
  -f config_files/feed_small.json \
  -p config_files/prompts.json \
  -x ReverseChrono \
  -y PreferentialAttachment
```

Use this when you need short feedback cycles.

## 3. Resume An Existing Population

```bash
python y_client.py \
  -c config_files/config.json \
  -p config_files/prompts.json \
  -a experiments/simulation_agents.json
```

This reloads stored agents instead of generating a new population.

## 4. Run With An Explicit Initial Graph

```bash
python y_client.py \
  -c config_files/config.json \
  -p config_files/prompts.json \
  -g config_files/sample_graph.csv
```

Use this when the initial follow graph matters for the experiment design.

## 5. Enable External Memory

In the chosen config file:

```json
{
  "simulation": {
    "name": "memory_eval"
  },
  "agents": {
    "memory_enabled": true,
    "memory_backend": "hybrid_semantic",
    "memory_prompt_mode": "subtle_timeline"
  }
}
```

Requirements:

- `YServer` must expose the `/memory/*` API
- `y_memory_subsystem` must be available in the sibling workspace expected by [`memory_runtime.py`](/Users/rossetti/PycharmProjects/YClient/y_client/memory_runtime.py)

## 6. Ollama-Based Local Setup

Example config fragment:

```json
{
  "servers": {
    "llm": "http://127.0.0.1:11434/v1",
    "llm_api_key": "NULL",
    "llm_v": "http://127.0.0.1:11434/v1",
    "llm_v_api_key": "NULL"
  },
  "agents": {
    "llm_agents": ["llama3.2"],
    "llm_v_agent": ["minicpm-v"]
  }
}
```

This is the simplest local OpenAI-compatible setup for development.
