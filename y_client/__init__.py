"""
Y Client Package

This package provides the main interfaces and classes for the Y social network simulation client.
It includes agent classes, time management, recommendation systems, and web client implementations.

Main exports:
    Legacy classes (require full dependencies):
        - Agent, PageAgent, FakeAgent, FakePageAgent (from y_client.classes)
        - SimulationSlot (from y_client.classes)
        - ContentRecSys, FollowRecSys (from y_client.recsys)
        - YClientWeb (from y_client.clients)
    
    New data classes (lightweight, minimal dependencies):
        - AgentData, PageAgentData, FakeAgentData, FakePageAgentData (from y_client.classes.agent_data)
        - agent_to_data, create_agent_data, wrap_agent_data (from y_client.classes.agent_factory)
    
    New functional modules (for Ray parallelization):
        - agent_functions (from y_client.functions.agent_functions)
        - agent_llm_functions (from y_client.functions.agent_llm_functions)
        - ray_integration (from y_client.functions.ray_integration)

Usage:
    # Import legacy classes (requires all dependencies installed)
    from y_client.classes import Agent, PageAgent
    
    # Import new data classes (minimal dependencies)
    from y_client.classes.agent_data import AgentData
    from y_client.functions.ray_integration import init_ray, execute_parallel_gpu
"""

# Define __all__ but don't eagerly import - let users import what they need
__all__ = [
    # Legacy classes - import from y_client.classes
    'Agent',
    'PageAgent', 
    'FakeAgent',
    'FakePageAgent',
    'SimulationSlot',
    'Agents',
    # New data classes - import from y_client.classes.agent_data
    'AgentData',
    'PageAgentData',
    'FakeAgentData',
    'FakePageAgentData',
    # Factory functions - import from y_client.classes.agent_factory
    'agent_to_data',
    'create_agent_data',
    'wrap_agent_data',
]

# Lazy import function for backward compatibility
def __getattr__(name):
    """
    Lazy import of module attributes.
    
    This allows the package to be imported without loading all dependencies,
    but still provides access to classes when explicitly requested.
    """
    if name in ('Agent', 'PageAgent', 'Agents'):
        from y_client.classes.base_agent import Agent, Agents
        from y_client.classes.page_agent import PageAgent
        if name == 'Agent':
            return Agent
        elif name == 'PageAgent':
            return PageAgent
        elif name == 'Agents':
            return Agents
    elif name in ('FakeAgent',):
        from y_client.classes.fake_base_agent import FakeAgent
        return FakeAgent
    elif name in ('FakePageAgent',):
        from y_client.classes.fake_page_agent import FakePageAgent
        return FakePageAgent
    elif name == 'SimulationSlot':
        from y_client.classes.time import SimulationSlot
        return SimulationSlot
    elif name in ('AgentData', 'PageAgentData', 'FakeAgentData', 'FakePageAgentData'):
        from y_client.classes.agent_data import AgentData, PageAgentData, FakeAgentData, FakePageAgentData
        if name == 'AgentData':
            return AgentData
        elif name == 'PageAgentData':
            return PageAgentData
        elif name == 'FakeAgentData':
            return FakeAgentData
        elif name == 'FakePageAgentData':
            return FakePageAgentData
    elif name in ('agent_to_data', 'create_agent_data', 'wrap_agent_data'):
        from y_client.classes.agent_factory import agent_to_data, create_agent_data, wrap_agent_data
        if name == 'agent_to_data':
            return agent_to_data
        elif name == 'create_agent_data':
            return create_agent_data
        elif name == 'wrap_agent_data':
            return wrap_agent_data
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
