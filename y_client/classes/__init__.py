"""
Classes Module

This module contains the core agent classes for the Y social network simulation.
It provides base agent functionality, page agents for news sources, time
management utilities, and new data class representations.

Exports:
    Legacy Classes:
        - Agent: Base agent class with social network interactions
        - PageAgent: Specialized agent for news page accounts
        - FakeAgent: Fake agent class for testing
        - FakePageAgent: Fake page agent for testing
        - SimulationSlot: Time management for the simulation
    
    Data Classes (new):
        - AgentData: Data class for agent state
        - PageAgentData: Data class for page agent state
        - FakeAgentData: Data class for fake agent state
        - FakePageAgentData: Data class for fake page agent state
    
    Factory Functions:
        - agent_to_data: Convert Agent to AgentData
        - create_agent_data: Create new AgentData instances
        - wrap_agent_data: Wrap AgentData with Agent-like interface
        - AgentDataWrapper: Wrapper class for AgentData
"""

# Legacy agent classes
from .base_agent import *
from .page_agent import *
from .fake_base_agent import FakeAgent
from .fake_page_agent import FakePageAgent
from .time import *

# New data classes
from .agent_data import (
    AgentData,
    PageAgentData,
    FakeAgentData,
    FakePageAgentData,
)

# Factory functions
from .agent_factory import (
    agent_to_data,
    create_agent_data,
    wrap_agent_data,
    AgentDataWrapper,
)
