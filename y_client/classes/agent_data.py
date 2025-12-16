"""
Agent Data Classes Module

This module provides data class definitions for agents in the Y social network simulation.
These lightweight data classes replace the previous object-oriented agent classes,
separating data storage from behavior (methods are now in separate functional modules).

The data classes use Python's @dataclass decorator for automatic initialization,
representation, and efficient memory usage. This design enables:
- Easy serialization/deserialization for Ray distributed computing
- Clear separation between data and behavior
- Better performance through reduced object overhead
- Simplified testing and debugging

Classes:
    - AgentData: Core data for individual user agents
    - PageAgentData: Data for news page agents (extends AgentData)
    - FakeAgentData: Data for fake/bot user agents (extends AgentData)
    - FakePageAgentData: Data for fake page agents (extends PageAgentData)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AgentData:
    """
    Data class representing an individual user agent in the Y social network.
    
    This class stores all state information for an agent including demographics,
    personality traits, interests, configuration, and interaction history.
    All behavior/methods have been extracted to functional modules.
    
    Attributes:
        # Identity and authentication
        name: Username of the agent
        email: Email address
        pwd: Password for authentication
        user_id: Unique identifier assigned by the server
        owner: Username of the agent owner/creator
        
        # Demographics
        age: Age of the user
        gender: Gender
        nationality: Nationality
        language: Primary language for content generation
        education_level: Education level
        profession: Professional occupation
        
        # Personality (Big Five model)
        oe: Openness to experience (0-1)
        co: Conscientiousness (0-1)
        ex: Extraversion (0-1)
        ag: Agreeableness (0-1)
        ne: Neuroticism (0-1)
        
        # Interests and opinions
        interests: List of topics/interests or count of interests
        leaning: Political leaning
        opinions: Dictionary of opinions on various topics
        archetype: Personality archetype
        
        # Behavior configuration
        type: LLM model type (e.g., "llama3", "gpt-4")
        toxicity: Toxicity level ("no", "low", "medium", "high")
        round_actions: Number of actions per time slot
        daily_activity_level: Activity level multiplier
        
        # System configuration
        base_url: Base URL for the API server
        llm_base: Base URL for LLM server
        llm_config: LLM configuration dictionary
        llm_v_config: Vision LLM configuration dictionary
        
        # Recommendation systems
        content_rec_sys: Content recommendation system instance
        follow_rec_sys: Follow recommendation system instance
        content_rec_sys_name: Name of the content recommendation system
        follow_rec_sys_name: Name of the follow recommendation system
        
        # Simulation state
        joined_on: Timestamp when agent joined the network
        is_page: Flag indicating if this is a page agent (1) or user (0)
        attention_window: Number of time slots to consider for recommendations
        
        # Prompts and configuration
        prompts: Dictionary of LLM prompts for various actions
        probability_of_daily_follow: Probability of following someone daily
        probability_of_secondary_follow: Probability of following after interaction
        emotions: List of emotion labels for annotation
        actions_likelihood: Dictionary of action probabilities
        
        # Opinion dynamics
        opinions_enabled: Whether opinion dynamics are enabled
        opinion_dynamics: Configuration for opinion dynamics model
        
        # Activity tracking
        activity_profile: Activity profile identifier
        annotate_emotions: Whether to annotate emotions in posts
        
        # Internal state
        topics_sentiment: Current sentiment on topics (used during generation)
        topics_opinions: Current opinions on topics (used during generation)
    """
    
    # Identity
    name: str
    email: str
    pwd: Optional[str] = None
    user_id: Optional[int] = None
    owner: Optional[str] = None
    
    # Demographics
    age: Optional[int] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    language: Optional[str] = None
    education_level: Optional[str] = None
    profession: Optional[str] = None
    
    # Personality (Big Five)
    oe: float = 0.5
    co: float = 0.5
    ex: float = 0.5
    ag: float = 0.5
    ne: float = 0.5
    
    # Interests and opinions
    interests: Any = None  # Can be list or int
    leaning: Optional[str] = None
    opinions: Optional[Dict] = None
    archetype: Optional[str] = None
    
    # Behavior
    type: str = "llama3"
    toxicity: str = "no"
    round_actions: int = 3
    daily_activity_level: int = 1
    
    # System configuration
    base_url: str = ""
    llm_base: str = ""
    llm_config: Dict = field(default_factory=dict)
    llm_v_config: Dict = field(default_factory=dict)
    
    # Recommendation systems
    content_rec_sys: Any = None
    follow_rec_sys: Any = None
    content_rec_sys_name: Optional[str] = None
    follow_rec_sys_name: Optional[str] = None
    
    # Simulation state
    joined_on: Optional[int] = None
    is_page: int = 0
    attention_window: int = 5
    
    # Prompts
    prompts: Optional[Dict] = None
    probability_of_daily_follow: float = 0.0
    probability_of_secondary_follow: float = 0.0
    emotions: List[str] = field(default_factory=list)
    actions_likelihood: Dict = field(default_factory=dict)
    
    # Opinion dynamics
    opinions_enabled: bool = False
    opinion_dynamics: Optional[Dict] = None
    
    # Activity
    activity_profile: Optional[str] = None
    annotate_emotions: bool = False
    
    # Internal state
    topics_sentiment: str = ""
    topics_opinions: str = ""


@dataclass
class PageAgentData(AgentData):
    """
    Data class for news page agents.
    
    Extends AgentData with page-specific attributes. Pages post news content
    from RSS feeds and don't perform regular user actions like commenting.
    
    Attributes:
        feed_url: URL of the RSS feed for this page
        (inherits all attributes from AgentData)
    """
    feed_url: Optional[str] = None
    is_page: int = 1  # Override default to mark as page


@dataclass
class FakeAgentData(AgentData):
    """
    Data class for fake/bot user agents.
    
    Identical to AgentData but used to differentiate fake agents that don't
    use LLMs for content generation, instead using simple fake data.
    This is useful for testing and performance optimization.
    """
    pass


@dataclass
class FakePageAgentData(PageAgentData):
    """
    Data class for fake page agents.
    
    Extends PageAgentData for pages that don't use LLMs.
    Used for testing and performance optimization.
    """
    pass
