# Social Feedback Loop

Recent YClient updates added a client-side social feedback pipeline that covers two related behaviors:

- stress/reward state reconstruction and churn evaluation
- reciprocal follow and unfollow decisions, including secondary follows

Both features respect the main client/server contract. The client performs LLM-based interpretation and decision making. The server remains the only component that writes the experiment database.

## Stress, Reward, And Churn

The microblogging client can optionally track two aggregate variables for each agent:

- `stress`
- `reward`

The feature is controlled through a top-level `stress_reward` block in the client configuration. The expected shape is:

```json
{
  "stress_reward": {
    "enabled": true,
    "backward_rounds": 24,
    "system": {
      "events": {},
      "coupling": {},
      "churn": {
        "enabled": false
      }
    }
  }
}
```

When enabled, the client refreshes the acting agent’s current aggregate state before it performs a social action. If churn is enabled inside `stress_reward.system.churn`, the client also computes the current churn probability and may ask the server to set `user_mgmt.left_on` for that agent.

For directed actions toward another user, the client computes variation deltas and sends only the resulting values to the server. The current implementation covers:

- reactions
- comments
- shares

Comment and share flows may call the LLM annotation prompts in `config_files/prompts.json`, specifically:

- `agent_comment_stress_reward_annotation`
- `agent_post_stress_reward_annotation`

Those prompts extract structured fields such as tone, directness, and support strength. The server never performs that annotation itself.

## Reciprocal Follow And Unfollow

The client also supports follow-back and unfollow-back evaluation after a real follow or unfollow event has been executed.

The main configuration knob is:

- `agents.probability_of_follow_back`

If the configured probability gate passes, the followed or unfollowed peer evaluates whether to create or remove the reciprocal edge. The check only runs when the reverse edge is currently missing for follow-back, or present for unfollow-back.

Rule-based agents only use the configured probability. LLM-backed agents additionally look at the profile of the user who initiated the relationship change before deciding.

This same mechanism applies to:

- direct follow/unfollow actions
- secondary follow actions triggered after content interactions

The client asks the server whether the reverse edge already exists through `/check_follow_relationship`, then submits the actual follow or unfollow only if the reciprocal action is still valid.

## Why This Matters

These two features create a tighter feedback loop than the older client behavior. Directed interactions now affect the recipient’s measured platform experience, while relationship changes can trigger immediate reciprocal network updates. Together, they make the microblogging runtime a better fit for experiments that study retention, exposure, and the downstream effects of interpersonal interaction.
