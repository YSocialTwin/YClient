"""
Agent Factory Module

This module provides factory functions and converters to work with both
legacy Agent classes and new AgentData classes. This allows gradual migration
and maintains backward compatibility.

Functions:
    - agent_to_data: Convert Agent instance to AgentData
    - data_to_agent: Convert AgentData to Agent instance (wrapper)
    - create_agent_data: Factory to create AgentData instances
    - create_agent: Factory to create Agent instances (delegates to legacy code)
"""

from typing import Dict, Any, Optional
from y_client.classes.agent_data import AgentData, PageAgentData, FakeAgentData, FakePageAgentData


def agent_to_data(agent) -> AgentData:
    """
    Convert a legacy Agent instance to AgentData.
    
    This extracts all state from an Agent object and creates a new AgentData
    instance. The AgentData can then be used with functional operations.
    
    Args:
        agent: Legacy Agent, PageAgent, FakeAgent, or FakePageAgent instance
    
    Returns:
        AgentData, PageAgentData, FakeAgentData, or FakePageAgentData instance
    """
    # Determine the appropriate data class based on agent type
    from y_client.classes.page_agent import PageAgent
    from y_client.classes.fake_base_agent import FakeAgent
    from y_client.classes.fake_page_agent import FakePageAgent
    
    if isinstance(agent, FakePageAgent):
        DataClass = FakePageAgentData
        extra_attrs = {'feed_url': getattr(agent, 'feed_url', None)}
    elif isinstance(agent, PageAgent):
        DataClass = PageAgentData
        extra_attrs = {'feed_url': getattr(agent, 'feed_url', None)}
    elif isinstance(agent, FakeAgent):
        DataClass = FakeAgentData
        extra_attrs = {}
    else:
        DataClass = AgentData
        extra_attrs = {}
    
    # Extract common attributes
    data = DataClass(
        # Identity
        name=agent.name,
        email=agent.email,
        pwd=getattr(agent, 'pwd', None),
        user_id=getattr(agent, 'user_id', None),
        owner=getattr(agent, 'owner', None),
        
        # Demographics
        age=getattr(agent, 'age', None),
        gender=getattr(agent, 'gender', None),
        nationality=getattr(agent, 'nationality', None),
        language=getattr(agent, 'language', None),
        education_level=getattr(agent, 'education_level', None),
        profession=getattr(agent, 'profession', None),
        
        # Personality (Big Five)
        oe=getattr(agent, 'oe', 0.5),
        co=getattr(agent, 'co', 0.5),
        ex=getattr(agent, 'ex', 0.5),
        ag=getattr(agent, 'ag', 0.5),
        ne=getattr(agent, 'ne', 0.5),
        
        # Interests and opinions
        interests=getattr(agent, 'interests', None),
        leaning=getattr(agent, 'leaning', None),
        opinions=getattr(agent, 'opinions', None),
        archetype=getattr(agent, 'archetype', None),
        
        # Behavior
        type=getattr(agent, 'type', 'llama3'),
        toxicity=getattr(agent, 'toxicity', 'no'),
        round_actions=getattr(agent, 'round_actions', 3),
        daily_activity_level=getattr(agent, 'daily_activity_level', 1),
        
        # System configuration
        base_url=getattr(agent, 'base_url', ''),
        llm_base=getattr(agent, 'llm_base', ''),
        llm_config=getattr(agent, 'llm_config', {}),
        llm_v_config=getattr(agent, 'llm_v_config', {}),
        
        # Recommendation systems
        content_rec_sys=getattr(agent, 'content_rec_sys', None),
        follow_rec_sys=getattr(agent, 'follow_rec_sys', None),
        content_rec_sys_name=getattr(agent, 'content_rec_sys_name', None),
        follow_rec_sys_name=getattr(agent, 'follow_rec_sys_name', None),
        
        # Simulation state
        joined_on=getattr(agent, 'joined_on', None),
        is_page=getattr(agent, 'is_page', 0),
        attention_window=getattr(agent, 'attention_window', 5),
        
        # Prompts and configuration
        prompts=getattr(agent, 'prompts', None),
        probability_of_daily_follow=getattr(agent, 'probability_of_daily_follow', 0.0),
        probability_of_secondary_follow=getattr(agent, 'probability_of_secondary_follow', 0.0),
        emotions=getattr(agent, 'emotions', []),
        actions_likelihood=getattr(agent, 'actions_likelihood', {}),
        
        # Opinion dynamics
        opinions_enabled=getattr(agent, 'opinions_enabled', False),
        opinion_dynamics=getattr(agent, 'opinion_dynamics', None),
        
        # Activity
        activity_profile=getattr(agent, 'activity_profile', None),
        annotate_emotions=getattr(agent, 'annotate_emotions', False),
        
        # Internal state
        topics_sentiment=getattr(agent, 'topics_sentiment', ''),
        topics_opinions=getattr(agent, 'topics_opinions', ''),
        
        # Extra attributes for subclasses
        **extra_attrs
    )
    
    return data


def create_agent_data(
    name: str,
    email: str,
    config: Dict,
    agent_class: str = "Agent",
    **kwargs
) -> AgentData:
    """
    Factory function to create AgentData instances.
    
    This is a convenient way to create AgentData without manually specifying
    all configuration parameters. It extracts configuration from the config dict
    and applies it to the AgentData.
    
    Args:
        name: Username
        email: Email address
        config: Configuration dictionary
        agent_class: Type of agent ("Agent", "PageAgent", "FakeAgent", "FakePageAgent")
        **kwargs: Additional agent attributes
    
    Returns:
        AgentData instance of the appropriate type
    """
    # Select the appropriate data class
    if agent_class == "FakePageAgent":
        DataClass = FakePageAgentData
    elif agent_class == "PageAgent":
        DataClass = PageAgentData
    elif agent_class == "FakeAgent":
        DataClass = FakeAgentData
    else:
        DataClass = AgentData
    
    # Extract configuration
    base_config = {
        'name': name,
        'email': email,
        'base_url': config['servers']['api'].rstrip('/'),
        'llm_base': config['servers']['llm'],
        'attention_window': int(config['agents']['attention_window']),
        'probability_of_daily_follow': float(config['agents']['probability_of_daily_follow']),
        'probability_of_secondary_follow': float(config['agents']['probability_of_secondary_follow']),
        'emotions': config['posts']['emotions'],
        'actions_likelihood': config['simulation']['actions_likelihood'],
        'opinion_dynamics': config['simulation'].get('opinion_dynamics'),
        'llm_v_config': {
            'url': config['servers']['llm_v'],
            'api_key': config['servers'].get('llm_v_api_key', 'NULL'),
            'model': config['servers'].get('llm_v_agent', 'minicpm-v'),
            'temperature': config['servers'].get('llm_v_temperature', 0.7),
            'max_tokens': int(config['servers'].get('llm_v_max_tokens', 512)),
        }
    }
    
    # Merge with provided kwargs
    base_config.update(kwargs)
    
    # Create and return AgentData
    return DataClass(**base_config)


class AgentDataWrapper:
    """
    Wrapper class that provides Agent-like interface using AgentData and functions.
    
    This allows using AgentData with functional operations while maintaining
    compatibility with code that expects Agent-like objects.
    """
    
    def __init__(self, agent_data: AgentData, use_ray: bool = False):
        """
        Initialize wrapper with AgentData.
        
        Args:
            agent_data: AgentData instance
            use_ray: Whether to use Ray for parallel execution
        """
        self.data = agent_data
        self.use_ray = use_ray
        
        # Import function modules
        from y_client.functions import agent_functions, agent_llm_functions
        self._cpu_funcs = agent_functions
        self._gpu_funcs = agent_llm_functions
        
        if use_ray:
            try:
                from y_client.functions import ray_integration
                self._ray = ray_integration
            except ImportError:
                print("Warning: Ray not available, falling back to sequential execution")
                self.use_ray = False
    
    def __getattr__(self, name):
        """
        Dynamically delegate attribute access to AgentData or function modules.
        
        This allows calling functions as if they were methods, e.g.:
            wrapper.post(tid=1)  # Calls agent_llm_functions.post_content(wrapper.data, 1)
        """
        # First try to get from data
        if hasattr(self.data, name):
            return getattr(self.data, name)
        
        # Try CPU functions
        if hasattr(self._cpu_funcs, name):
            func = getattr(self._cpu_funcs, name)
            return lambda *args, **kwargs: func(self.data, *args, **kwargs)
        
        # Try GPU functions
        if hasattr(self._gpu_funcs, name):
            func = getattr(self._gpu_funcs, name)
            return lambda *args, **kwargs: func(self.data, *args, **kwargs)
        
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def to_dict(self) -> Dict:
        """Convert AgentData to dictionary."""
        from dataclasses import asdict
        return asdict(self.data)


# Convenience aliases
def wrap_agent_data(agent_data: AgentData, use_ray: bool = False) -> AgentDataWrapper:
    """
    Wrap AgentData in a class that provides Agent-like interface.
    
    Args:
        agent_data: AgentData instance
        use_ray: Whether to use Ray for execution
    
    Returns:
        AgentDataWrapper instance
    """
    return AgentDataWrapper(agent_data, use_ray)


__all__ = [
    'agent_to_data',
    'create_agent_data',
    'AgentDataWrapper',
    'wrap_agent_data',
]
