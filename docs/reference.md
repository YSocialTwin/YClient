# Reference Notes

## CLI Parameters

The main CLI parameters are defined in [`y_client.py`](/Users/rossetti/PycharmProjects/YClient/y_client.py).

| Flag | Long form | Meaning |
| --- | --- | --- |
| `-c` | `--config_file` | main simulation JSON |
| `-f` | `--feeds` | RSS feed config |
| `-p` | `--prompts` | prompt template JSON |
| `-a` | `--agents` | existing agent dump |
| `-o` | `--owner` | owner label for generated agents |
| `-r` | `--reset` | reset server-side experiment state |
| `-n` | `--news` | reload feed/news database |
| `-x` | `--crecsys` | content recommender class |
| `-y` | `--frecsys` | follow recommender class |
| `-g` | `--graph` | initial social graph CSV |

## Recommender Selection Guidance

- `ReverseChronoFollowersPopularity`
  - balanced default for timeline realism
- `ReverseChrono`
  - useful for debugging because ordering is simple
- `PreferentialAttachment`
  - suitable when you want a plausible skew in follow growth

## Practical Tuning Advice

- reduce `starting_agents`, `days`, and `slots` first when debugging
- lower `llm_temperature` if outputs are too noisy
- keep `memory_enabled=false` unless the matching server branch is active
- use `feed_small.json` instead of the full feed catalog for tight local loops
