"""
Example script demonstrating the agent execution time logging system.

This script shows how to:
1. Configure a custom log file location
2. Run agent operations
3. Analyze the resulting logs
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Example: Setting up logging programmatically
def example_custom_log_path():
    """Example of using a custom log file path"""
    
    # Option 1: Pass log_file parameter when creating client
    # from y_client.clients import YClientBase
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs/simulation_run_1")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = str(log_dir / "agent_execution.log")
    
    print(f"Creating client with log file: {log_file}")
    
    # Note: This is a simplified example. In practice, you would need
    # valid config and prompts files
    # client = YClientBase(
    #     config_filename="config_files/config.json",
    #     prompts_filename="config_files/prompts.json",
    #     log_file=log_file
    # )
    
    print(f"All agent method executions will be logged to: {log_file}")


def analyze_logs(log_file):
    """Analyze execution time logs"""
    
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    print(f"\nAnalyzing log file: {log_file}\n")
    
    # Read all log entries
    logs = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line")
    
    if not logs:
        print("No log entries found")
        return
    
    print(f"Total log entries: {len(logs)}")
    
    # Group by method
    from collections import defaultdict
    method_stats = defaultdict(lambda: {'times': [], 'errors': 0, 'agents': set()})
    
    for log in logs:
        method = log['method_name']
        method_stats[method]['times'].append(log['execution_time_seconds'])
        method_stats[method]['agents'].add(log['agent_name'])
        if not log['success']:
            method_stats[method]['errors'] += 1
    
    # Print statistics
    print("\nMethod Execution Statistics:")
    print("-" * 80)
    print(f"{'Method':<25} {'Calls':<8} {'Agents':<8} {'Avg Time (s)':<15} {'Total Time (s)':<15} {'Errors'}")
    print("-" * 80)
    
    for method, stats in sorted(method_stats.items()):
        times = stats['times']
        avg_time = sum(times) / len(times)
        total_time = sum(times)
        num_agents = len(stats['agents'])
        num_calls = len(times)
        errors = stats['errors']
        
        print(f"{method:<25} {num_calls:<8} {num_agents:<8} {avg_time:<15.4f} {total_time:<15.4f} {errors}")
    
    print("-" * 80)
    
    # Show slowest method calls
    print("\nSlowest 5 Method Calls:")
    print("-" * 80)
    print(f"{'Agent':<20} {'Method':<25} {'Time (s)':<15} {'Timestamp'}")
    print("-" * 80)
    
    sorted_logs = sorted(logs, key=lambda x: x['execution_time_seconds'], reverse=True)[:5]
    for log in sorted_logs:
        print(f"{log['agent_name']:<20} {log['method_name']:<25} {log['execution_time_seconds']:<15.4f} {log['timestamp']}")
    
    print("-" * 80)
    
    # Show agents by activity
    agent_activity = defaultdict(int)
    for log in logs:
        agent_activity[log['agent_name']] += 1
    
    print("\nMost Active Agents:")
    print("-" * 80)
    print(f"{'Agent Name':<30} {'Total Actions'}")
    print("-" * 80)
    
    for agent, count in sorted(agent_activity.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{agent:<30} {count}")
    
    print("-" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("Agent Execution Time Logging Example")
    print("=" * 80)
    
    # Show how to configure custom log path
    example_custom_log_path()
    
    # Example: Analyze an existing log file
    # Uncomment and modify the path to analyze your actual log file
    # analyze_logs("logs/simulation_run_1/agent_execution.log")
    
    print("\n" + "=" * 80)
    print("For more information, see docs/logging.md")
    print("=" * 80)
