# Agent Execution Time Logging

This document describes the logging system for tracking execution time of agent public methods.

## Overview

The logging system automatically tracks the execution time of all public methods in Agent and PageAgent classes. Each execution is logged as a JSON object in a log file, allowing for detailed performance analysis and monitoring.

## Features

- **JSON Format**: Each log entry is a single-line JSON object for easy parsing
- **Configurable Log Path**: Specify the log file location at client creation time
- **Rotating Log Files**: Automatic log rotation to prevent unbounded log growth
- **Automatic Tracking**: Public methods are automatically logged via decorators
- **Error Handling**: Failed method executions are also logged with error details
- **Minimal Overhead**: Lightweight decorator with minimal performance impact

## Log Entry Format

Each log entry contains the following fields:

```json
{
  "time": "2025-11-01 11:38:53",
  "agent_name": "CharlesHarris",
  "method_name": "comment",
  "execution_time_seconds": 1.6934,
  "success": true,
  "tid": 108,
  "day": 4,
  "hour": 12
}
```

### Fields

- **time**: Timestamp in format 'YYYY-MM-DD HH:MM:SS' (UTC)
- **agent_name**: Name of the agent executing the method
- **method_name**: Name of the method being executed
- **execution_time_seconds**: Time taken to execute the method in seconds (4 decimal places)
- **success**: Boolean indicating if the method completed successfully
- **tid**: (optional) Time slot ID when the method was called
- **day**: (optional) Simulation day calculated from tid (tid // 24)
- **hour**: (optional) Simulation hour calculated from tid (tid % 24)
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

# Get all actions on a specific simulation day
cat agent_execution.log | jq -r 'select(.day==4)'

# Group by hour to see activity patterns
cat agent_execution.log | jq -r '.hour' | sort -n | uniq -c
```

## Best Practices

1. **Use Descriptive Paths**: Place logs in organized directories (e.g., `logs/simulation_name/`)
2. **Monitor Performance**: Regularly analyze logs to identify performance bottlenecks
3. **Archive Logs**: Keep logs for each simulation run for reproducibility and debugging

## Log Rotation

The logging system automatically rotates log files to prevent unbounded growth during long-running simulations. When a log file exceeds the configured maximum size, it is renamed with a numeric suffix (e.g., `.1`, `.2`) and a new log file is created.

### Default Settings

- **Maximum file size**: 10 MB per log file
- **Backup count**: 5 backup files

With default settings, log files are rotated as follows:
- `agent_execution.log` - current log file
- `agent_execution.log.1` - most recent backup
- `agent_execution.log.2` - older backup
- ... up to `agent_execution.log.5`

When the backup count is exceeded, the oldest backup file is deleted.

### Configuring Rotation

You can customize log rotation settings using the `set_logger` function:

```python
from y_client.logger import set_logger

# Configure custom rotation settings
# max_bytes: Maximum size per log file in bytes (default: 10 MB)
# backup_count: Number of backup files to keep (default: 5)
set_logger(
    log_file="logs/agent_execution.log",
    max_bytes=5 * 1024 * 1024,  # 5 MB per file
    backup_count=10  # Keep 10 backup files
)
```

### Example Scenarios

**Small simulation (short-term)**:
```python
set_logger("simulation.log", max_bytes=1024*1024, backup_count=2)  # 1 MB, 2 backups
```

**Large-scale simulation (long-term)**:
```python
set_logger("simulation.log", max_bytes=50*1024*1024, backup_count=20)  # 50 MB, 20 backups
```

## Implementation Details

The logging system uses a decorator pattern (`@log_execution_time`) applied to public methods. The decorator:

1. Captures the start time before method execution
2. Executes the original method
3. Captures the end time after execution
4. Calculates execution time
5. Writes the log entry to the configured log file

The global logger is configured once at client initialization and reused for all subsequent logging operations.

### Rotating File Handler

The logger uses Python's `RotatingFileHandler` from the `logging.handlers` module to implement log rotation. This provides:

- **Automatic rotation**: When a log file exceeds the maximum size, it's automatically rotated
- **Configurable limits**: Set custom file sizes and backup counts
- **Thread-safe**: Safe for use in multi-threaded environments
- **UTF-8 encoding**: Proper handling of Unicode characters in log entries
