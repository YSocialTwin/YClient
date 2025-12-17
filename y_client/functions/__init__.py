"""
Agent Functions Package

This package contains functional modules for agent operations, organized by
computational requirements (CPU-bound vs GPU-bound) for efficient Ray parallelization.

Modules:
    - agent_functions: CPU-bound operations (reading, searching, following, etc.)
    - agent_llm_functions: GPU-bound operations (LLM-based content generation)
    - ray_integration: Ray parallelization wrappers

Usage:
    # Import specific modules directly
    from y_client.functions.agent_functions import read_posts, follow_action
    from y_client.functions.agent_llm_functions import post_content
    from y_client.functions.ray_integration import init_ray, execute_parallel_gpu
    
    # Or import the module
    from y_client.functions import agent_functions
    agent_functions.read_posts(agent_data)
"""

# Don't eagerly import anything - let users import what they need directly
__all__ = ['agent_functions', 'agent_llm_functions', 'ray_integration']

