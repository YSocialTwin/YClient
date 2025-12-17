"""
Classes Module

This module contains the core agent classes for the Y social network simulation.
It provides base agent functionality, page agents for news sources, time
management utilities, and new data class representations.

Exports:
    Legacy Classes (require full dependencies):
        - Agent: Base agent class with social network interactions
        - PageAgent: Specialized agent for news page accounts
        - FakeAgent: Fake agent class for testing
        - FakePageAgent: Fake page agent for testing
        - SimulationSlot: Time management for the simulation
        - Agents: Collection/manager for multiple Agent instances
    
    Data Classes (minimal dependencies):
        - AgentData: Data class for agent state
        - PageAgentData: Data class for page agent state
        - FakeAgentData: Data class for fake agent state
        - FakePageAgentData: Data class for fake page agent state
    
    Factory Functions:
        - agent_to_data: Convert Agent to AgentData
        - create_agent_data: Create new AgentData instances
        - wrap_agent_data: Wrap AgentData with Agent-like interface
        - AgentDataWrapper: Wrapper class for AgentData

Usage:
    # Import legacy classes (requires all dependencies)
    from y_client.classes import Agent, PageAgent
    
    # Import new data classes (minimal dependencies)
    from y_client.classes.agent_data import AgentData
    from y_client.classes.agent_factory import create_agent_data
"""

__all__ = [
    # Legacy classes
    'Agent',
    'Agents',
    'PageAgent',
    'FakeAgent',
    'FakePageAgent',
    'SimulationSlot',
    # Data classes
    'AgentData',
    'PageAgentData',
    'FakeAgentData',
    'FakePageAgentData',
    # Factory
    'agent_to_data',
    'create_agent_data',
    'wrap_agent_data',
    'AgentDataWrapper',
]


def __getattr__(name):
    """
    Lazy import of module attributes.
    
    This allows importing data classes without loading legacy dependencies.
    """
    # Legacy classes - require full dependencies
    if name in ('Agent', 'Agents'):
        from .base_agent import Agent, Agents
        return Agent if name == 'Agent' else Agents
    elif name == 'PageAgent':
        from .page_agent import PageAgent
        return PageAgent
    elif name == 'FakeAgent':
        from .fake_base_agent import FakeAgent
        return FakeAgent
    elif name == 'FakePageAgent':
        from .fake_page_agent import FakePageAgent
        return FakePageAgent
    elif name == 'SimulationSlot':
        from .time import SimulationSlot
        return SimulationSlot
    
    # Data classes - minimal dependencies
    elif name in ('AgentData', 'PageAgentData', 'FakeAgentData', 'FakePageAgentData'):
        from .agent_data import AgentData, PageAgentData, FakeAgentData, FakePageAgentData
        return {
            'AgentData': AgentData,
            'PageAgentData': PageAgentData,
            'FakeAgentData': FakeAgentData,
            'FakePageAgentData': FakePageAgentData,
        }[name]
    
    # Factory functions
    elif name in ('agent_to_data', 'create_agent_data', 'wrap_agent_data', 'AgentDataWrapper'):
        from .agent_factory import agent_to_data, create_agent_data, wrap_agent_data, AgentDataWrapper
        return {
            'agent_to_data': agent_to_data,
            'create_agent_data': create_agent_data,
            'wrap_agent_data': wrap_agent_data,
            'AgentDataWrapper': AgentDataWrapper,
        }[name]
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
