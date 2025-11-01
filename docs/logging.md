# Agent Execution Time Logging

This document describes the logging system for tracking execution time of agent public methods.

## Overview

The logging system automatically tracks the execution time of all public methods in Agent and PageAgent classes. Each execution is logged as a JSON object in a log file, allowing for detailed performance analysis and monitoring.

## Features

- **JSON Format**: Each log entry is a single-line JSON object for easy parsing
- **Configurable Log Path**: Specify the log file location at client creation time
- **Automatic Tracking**: Public methods are automatically logged via decorators
- **Error Handling**: Failed method executions are also logged with error details
- **Minimal Overhead**: Lightweight decorator with minimal performance impact

## Log Entry Format

Each log entry contains the following fields:

```json
{
  "timestamp": "2025-11-01T06:09:20.020355",
  "agent_name": "Agent1",
  "method_name": "post",
  "execution_time_seconds": 0.0501,
  "success": true,
  "args": {
    "tid": 5,
    "post_id": 42
  }
}
```

### Fields

- **timestamp**: UTC timestamp in ISO 8601 format
- **agent_name**: Name of the agent executing the method
- **method_name**: Name of the method being executed
- **execution_time_seconds**: Time taken to execute the method in seconds (4 decimal places)
- **success**: Boolean indicating if the method completed successfully
- **args**: (optional) Dictionary containing relevant method arguments (tid, post_id, etc.)
- **error**: (optional) Error message if the method failed

## Usage

### Command Line

When running the client from the command line, use the `-l` or `--log_file` flag to specify the log file location:

```bash
python y_client.py -c config_files/config.json -l logs/agent_execution.log
```

If not specified, logs will be written to `agent_execution.log` in the current directory.

### Programmatic Usage

When creating a client programmatically, pass the `log_file` parameter:

```python
from y_client.clients import YClientBase

# Create client with custom log file
client = YClientBase(
    config_filename="config_files/config.json",
    prompts_filename="config_files/prompts.json",
    log_file="logs/my_simulation.log"
)
```

For web-based clients:

```python
from y_client.clients import YClientWeb

# Create web client with custom log file
client = YClientWeb(
    config_file=config_dict,
    data_base_path="config_files/",
    log_file="/var/log/ysocial/agent_execution.log"
)
```

## Logged Methods

The following public methods are automatically logged:

### Agent Class
- `post(tid)` - Post original content
- `comment(post_id, tid, max_length_threads)` - Comment on a post
- `share(post_id, tid)` - Share a news article
- `reaction(post_id, tid, check_follow)` - Like/dislike a post
- `follow(tid, target, post_id, action)` - Follow/unfollow a user
- `cast(post_id, tid)` - Cast a voting intention
- `select_action(tid, actions, max_length_thread_reading)` - Select and perform an action
- `reply(tid, max_length_thread_reading)` - Reply to a mention
- `read(article)` - Read posts from feed
- `search()` - Search for posts
- `search_follow()` - Search for users to follow
- `comment_image(image, tid, article_id)` - Comment on an image

### PageAgent Class
- `select_action(tid, actions, max_length_thread_reading)` - Post news content
- `news(tid, article, website)` - Post a news article

## Analyzing Logs

### Using Python

```python
import json

# Read and parse log file
with open('agent_execution.log', 'r') as f:
    logs = [json.loads(line) for line in f]

# Calculate average execution time per method
from collections import defaultdict

method_times = defaultdict(list)
for log in logs:
    method_times[log['method_name']].append(log['execution_time_seconds'])

for method, times in method_times.items():
    avg_time = sum(times) / len(times)
    print(f"{method}: {avg_time:.4f}s avg ({len(times)} calls)")
```

### Using Command Line Tools

```bash
# Count executions per method
cat agent_execution.log | jq -r '.method_name' | sort | uniq -c

# Get average execution time for 'post' method
cat agent_execution.log | jq -r 'select(.method_name=="post") | .execution_time_seconds' | awk '{sum+=$1; count++} END {print sum/count}'

# Find failed method calls
cat agent_execution.log | jq -r 'select(.success==false)'

# Get execution times for a specific agent
cat agent_execution.log | jq -r 'select(.agent_name=="Agent1")'
```

## Best Practices

1. **Use Descriptive Paths**: Place logs in organized directories (e.g., `logs/simulation_name/`)
2. **Rotate Logs**: For long-running simulations, consider log rotation to prevent large files
3. **Monitor Performance**: Regularly analyze logs to identify performance bottlenecks
4. **Archive Logs**: Keep logs for each simulation run for reproducibility and debugging

## Implementation Details

The logging system uses a decorator pattern (`@log_execution_time`) applied to public methods. The decorator:

1. Captures the start time before method execution
2. Executes the original method
3. Captures the end time after execution
4. Calculates execution time
5. Writes the log entry to the configured log file

The global logger is configured once at client initialization and reused for all subsequent logging operations.
