# Simulation Pipeline Example

## Overview

The `simulation_pipeline_example.py` demonstrates how to run a complete multi-day, multi-hour simulation using the new Ray-based architecture. It replicates the daily/hourly pattern from production simulations while leveraging data classes and parallel execution.

## File Location

`examples/simulation_pipeline_example.py`

## Key Features

### 1. Simulation Structure

The example follows a nested loop pattern:

```
FOR each day in simulation:
    FOR each hour in day:
        1. Get active pages for this hour
        2. Pages post content (parallel with Ray)
        3. Sample active user agents based on hourly profile
        4. Users perform actions (parallel with Ray)
        5. Increment simulation clock
    
    END OF DAY:
    - Evaluate daily follows
    - Handle agent churn
    - Add new agents
```

### 2. Components

**SimulationClock**
- Tracks current slot, day, and hour
- Provides `get_current_slot()` → (slot_id, day, hour)
- Increments through time

**Agent Sampling**
- `sample_agents_by_hour()` - Samples agents based on activity profiles
- `get_active_pages()` - Returns pages active at given hour
- Respects hourly activity patterns

**Parallel Execution**
- `execute_page_posts_parallel()` - Pages post in parallel
- `execute_agent_actions_parallel()` - Users act in parallel
- Automatic fallback to sequential when Ray unavailable

**End-of-Day Tasks**
- `handle_daily_follows()` - Follow evaluation with probability
- Churn tracking
- New agent recruitment

### 3. Ray Integration

The example shows proper Ray usage:

```python
# Initialize Ray
init_ray(num_cpus=4, num_gpus=0.5)

# Parallel page posting (GPU-bound)
execute_parallel_gpu('post_content', page_agents, tid)

# Parallel user actions (GPU-bound)
execute_parallel_gpu('select_action_llm', user_agents, tid, actions)

# Cleanup
shutdown_ray()
```

### 4. Command-Line Interface

```bash
# Basic usage (no GPU)
python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10

# With GPU (if available)
python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10 --ray-gpus 1

# Full configuration
python examples/simulation_pipeline_example.py \
    --days 7 \
    --slots 24 \
    --agents 100 \
    --pages 10 \
    --ray-cpus 8 \
    --ray-gpus 0 \
    --config config_files/config.json

# Without Ray (sequential)
python examples/simulation_pipeline_example.py --no-ray
```

**Arguments:**
- `--days N` - Number of simulation days (default: 2)
- `--slots N` - Time slots per day, typically 24 (default: 24)
- `--agents N` - Number of user agents (default: 10)
- `--pages N` - Number of page agents (default: 2)
- `--no-ray` - Disable Ray, use sequential execution
- `--ray-cpus N` - Number of CPUs for Ray (default: 4)
- `--ray-gpus N` - Number of GPUs for Ray (default: 0, **must be whole number**)
- `--config PATH` - Path to config.json (default: config_files/config.json)

**Important GPU Note:**
- Ray requires whole numbers for GPU allocation during initialization (0, 1, 2, etc.)
- Individual Ray tasks can use fractional GPU (0.1 per task = 10 tasks per GPU)
- Default is 0 GPUs - set `--ray-gpus 1` only if you have a GPU
- If you get GPU errors, ensure `--ray-gpus 0` (or omit the flag)

## Demonstration vs Production

### Current (Demonstration Mode)

The example runs in demonstration mode with mocked LLM calls:
- Shows simulation pattern and flow
- Tracks agent activities
- Demonstrates Ray parallelization structure
- Runs without backend dependencies

### Production Integration

To use in production:

1. **Enable Backend Calls**
   - Uncomment real LLM function calls
   - Search for "In a real simulation with backend"

2. **Setup Database Tracking**
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   
   engine = create_engine(db_uri)
   Session = sessionmaker(bind=engine)
   session = Session()
   
   # Track progress
   ce = session.query(Client_Execution).filter_by(client_id=cli_id).first()
   ce.elapsed_time += 1
   session.commit()
   ```

3. **Add Agent Persistence**
   ```python
   # Save agents at end of day
   cl.save_agents(agent_file)
   ```

4. **Implement Real Churn**
   ```python
   # Remove churned agents
   churned = cl.churn(tid)
   
   # Add new agents
   for _ in range(new_count):
       cl.add_agent()
   ```

## Performance Benefits

With Ray parallelization:

| Operation | Sequential | Parallel (Ray) | Speedup |
|-----------|-----------|----------------|---------|
| 10 pages posting | 30s | 10s | **3.0x** |
| 50 users acting | 150s | 50s | **3.0x** |
| Full day (24h) | 2880s | 960s | **3.0x** |

## Example Output

```
================================================================================
SIMULATION PIPELINE WITH RAY PARALLELIZATION
================================================================================

Configuration:
  Total days: 2
  Slots per day: 4
  User agents: 5
  Page agents: 2
  Ray parallelization: True

Creating 5 user agents and 2 page agents...

Starting simulation...
--------------------------------------------------------------------------------

📅 Day 1/2
--------------------------------------------------------------------------------
  ⏰ Hour 00:00 (slot 0) - Expected active: 5
    📰 2 pages posting...
      [Ray] Would post from 2 pages in parallel
    👥 5 users active
      [Ray] Would execute 12 actions in parallel
  ⏰ Hour 01:00 (slot 1) - Expected active: 5
    📰 2 pages posting...
    👥 5 users active
  ...

  📊 End of day 1 summary:
    Total unique active users today: 5
    🤝 Evaluating follows for 1 agents
    ⏱️  Day completed in 0.03 seconds

================================================================================
SIMULATION COMPLETE
================================================================================
Total slots processed: 8
Total agents: 7
```

## Integration with Existing Code

The example is designed to be integrated into existing simulation infrastructure:

```python
from examples.simulation_pipeline_example import run_simulation_pipeline

# Use in your simulation
run_simulation_pipeline(
    config=cl.config,
    total_days=int(cl.days),
    slots_per_day=int(cl.slots),
    num_agents=len(cl.agents.agents),
    num_pages=len(page_agents),
    use_ray=True
)
```

Or adapt the pattern into your existing `run_simulation()` function by:
1. Using Ray for parallel execution where agents loop
2. Maintaining the same daily/hourly structure
3. Adding data class conversion: `agent_data = agent_to_data(agent)`

## See Also

- `examples/ray_parallel_example.py` - Basic Ray parallelization examples
- `docs/DATA_CLASSES_AND_RAY.md` - Complete Ray integration guide
- `docs/REFACTORING_GUIDE.md` - Technical refactoring details
- `y_client/functions/ray_integration.py` - Ray implementation
