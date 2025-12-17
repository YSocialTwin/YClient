"""
Ray Integration Module

This module provides Ray remote function wrappers for parallel execution of agent operations.
Functions are annotated to run on CPU or GPU resources based on their computational requirements.

CPU-bound functions: General operations that don't require GPUs
GPU-bound functions: LLM inference operations that benefit from GPU acceleration

Usage:
    import ray
    ray.init()
    
    # Execute CPU-bound function remotely
    result_ref = cpu_read_posts.remote(agent_data)
    result = ray.get(result_ref)
    
    # Execute GPU-bound function remotely (with GPU)
    result_ref = gpu_post_content.remote(agent_data, tid)
    result = ray.get(result_ref)
"""

import logging

logger = logging.getLogger(__name__)

try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray is not installed. Parallel execution will not be available. Install with: pip install ray")

# Use relative imports to avoid triggering package __init__.py
from . import agent_functions
from . import agent_llm_functions


# ============================================================================
# CPU-bound Remote Functions
# ============================================================================
# These functions execute general operations without GPU requirements

if RAY_AVAILABLE:
    @ray.remote
    def cpu_extract_components(text: str, c_type: str = "hashtags"):
        """Remote: Extract hashtags or mentions from text."""
        return agent_functions.extract_components(text, c_type)

    @ray.remote
    def cpu_get_user_from_post(agent_data, post_id: int):
        """Remote: Get user from post."""
        return agent_functions.get_user_from_post(agent_data, post_id)

    @ray.remote
    def cpu_get_article(agent_data, post_id: int):
        """Remote: Get article data."""
        return agent_functions.get_article(agent_data, post_id)

    @ray.remote
    def cpu_get_post(agent_data, post_id: int):
        """Remote: Get post content."""
        return agent_functions.get_post(agent_data, post_id)

    @ray.remote
    def cpu_get_thread(agent_data, post_id: int, max_tweets=None):
        """Remote: Get conversation thread."""
        return agent_functions.get_thread(agent_data, post_id, max_tweets)

    @ray.remote
    def cpu_get_interests(agent_data, tid: int):
        """Remote: Get agent interests."""
        return agent_functions.get_interests(agent_data, tid)

    @ray.remote
    def cpu_get_opinions(agent_data):
        """Remote: Get agent opinions."""
        return agent_functions.get_opinions(agent_data)

    @ray.remote
    def cpu_update_user_interests(agent_data, post_id: int, tid: int):
        """Remote: Update user interests."""
        return agent_functions.update_user_interests(agent_data, post_id, tid)

    @ray.remote
    def cpu_follow_action(agent_data, tid: int, target=None, post_id=None, action="follow"):
        """Remote: Follow/unfollow action."""
        return agent_functions.follow_action(agent_data, tid, target, post_id, action)

    @ray.remote
    def cpu_read_posts(agent_data, article: bool = False):
        """Remote: Read posts from recommendation system."""
        return agent_functions.read_posts(agent_data, article)

    @ray.remote
    def cpu_read_mentions(agent_data):
        """Remote: Read mentions."""
        return agent_functions.read_mentions(agent_data)

    @ray.remote
    def cpu_search_posts(agent_data):
        """Remote: Search posts."""
        return agent_functions.search_posts(agent_data)

    @ray.remote
    def cpu_search_follow_suggestions(agent_data):
        """Remote: Get follow suggestions."""
        return agent_functions.search_follow_suggestions(agent_data)

    @ray.remote
    def cpu_get_followers(agent_data):
        """Remote: Get followers."""
        return agent_functions.get_followers(agent_data)

    @ray.remote
    def cpu_get_timeline(agent_data):
        """Remote: Get timeline."""
        return agent_functions.get_timeline(agent_data)

    @ray.remote
    def cpu_churn_system(agent_data, tid: int):
        """Remote: Mark agent as churned."""
        return agent_functions.churn_system(agent_data, tid)


# ============================================================================
# GPU-bound Remote Functions
# ============================================================================
# These functions require GPU resources for LLM inference

if RAY_AVAILABLE:
    @ray.remote(num_gpus=0.1)  # Request fractional GPU - adjust based on your setup
    def gpu_post_content(agent_data, tid: int):
        """Remote (GPU): Generate and post content using LLM."""
        return agent_llm_functions.post_content(agent_data, tid)

    @ray.remote(num_gpus=0.1)
    def gpu_comment_on_post(agent_data, post_id: int, tid: int, max_length_threads=None):
        """Remote (GPU): Generate and post comment using LLM."""
        return agent_llm_functions.comment_on_post(agent_data, post_id, tid, max_length_threads)

    @ray.remote(num_gpus=0.1)
    def gpu_share_post(agent_data, post_id: int, tid: int):
        """Remote (GPU): Share post with LLM-generated commentary."""
        return agent_llm_functions.share_post(agent_data, post_id, tid)

    @ray.remote(num_gpus=0.1)
    def gpu_reaction_to_post(agent_data, post_id: int, tid: int, check_follow: bool = True):
        """Remote (GPU): Generate reaction using LLM decision."""
        return agent_llm_functions.reaction_to_post(agent_data, post_id, tid, check_follow)

    @ray.remote(num_gpus=0.1)
    def gpu_cast_vote(agent_data, post_id: int, tid: int):
        """Remote (GPU): Cast vote using LLM."""
        return agent_llm_functions.cast_vote(agent_data, post_id, tid)

    @ray.remote(num_gpus=0.1)
    def gpu_evaluate_follow(agent_data, post_text: str, post_id: int, action: str, tid: int):
        """Remote (GPU): Evaluate follow action using LLM."""
        return agent_llm_functions.evaluate_follow(agent_data, post_text, post_id, action, tid)

    @ray.remote(num_gpus=0.1)
    def gpu_select_action_llm(agent_data, tid: int, actions, max_length_thread_reading: int = 5):
        """Remote (GPU): Select action using LLM."""
        return agent_llm_functions.select_action_llm(agent_data, tid, actions, max_length_thread_reading)

    @ray.remote(num_gpus=0.1)
    def gpu_emotion_annotation(agent_data, text_to_annotate: str):
        """Remote (GPU): Annotate emotions using LLM."""
        return agent_llm_functions.emotion_annotation(agent_data, text_to_annotate)

    @ray.remote(num_gpus=0.1)
    def gpu_update_opinions(agent_data, post_id: int, tid: int, text: str):
        """Remote (GPU): Update opinions with possible LLM evaluation."""
        return agent_llm_functions.update_opinions(agent_data, post_id, tid, text)


# ============================================================================
# Batch Execution Utilities
# ============================================================================

# Registry of CPU-bound remote functions
CPU_FUNCTION_REGISTRY = {}
GPU_FUNCTION_REGISTRY = {}

def _register_functions():
    """Register remote functions to avoid using globals()."""
    if RAY_AVAILABLE:
        CPU_FUNCTION_REGISTRY.update({
            'extract_components': cpu_extract_components,
            'get_user_from_post': cpu_get_user_from_post,
            'get_article': cpu_get_article,
            'get_post': cpu_get_post,
            'get_thread': cpu_get_thread,
            'get_interests': cpu_get_interests,
            'get_opinions': cpu_get_opinions,
            'update_user_interests': cpu_update_user_interests,
            'follow_action': cpu_follow_action,
            'read_posts': cpu_read_posts,
            'read_mentions': cpu_read_mentions,
            'search_posts': cpu_search_posts,
            'search_follow_suggestions': cpu_search_follow_suggestions,
            'get_followers': cpu_get_followers,
            'get_timeline': cpu_get_timeline,
            'churn_system': cpu_churn_system,
        })
        
        GPU_FUNCTION_REGISTRY.update({
            'post_content': gpu_post_content,
            'comment_on_post': gpu_comment_on_post,
            'share_post': gpu_share_post,
            'reaction_to_post': gpu_reaction_to_post,
            'cast_vote': gpu_cast_vote,
            'evaluate_follow': gpu_evaluate_follow,
            'select_action_llm': gpu_select_action_llm,
            'emotion_annotation': gpu_emotion_annotation,
            'update_opinions': gpu_update_opinions,
        })


def execute_parallel_cpu(function_name: str, agent_data_list, *args, **kwargs):
    """
    Execute a CPU-bound function in parallel for multiple agents.
    
    Args:
        function_name: Name of the function to execute (e.g., 'read_posts')
        agent_data_list: List of AgentData instances
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        List of results in the same order as agent_data_list
    
    Raises:
        ValueError: If function_name is not a registered CPU function
    """
    if not RAY_AVAILABLE:
        # Fallback to sequential execution
        func = getattr(agent_functions, function_name)
        return [func(agent_data, *args, **kwargs) for agent_data in agent_data_list]
    
    if function_name not in CPU_FUNCTION_REGISTRY:
        raise ValueError(f"Unknown CPU function: {function_name}. Available: {list(CPU_FUNCTION_REGISTRY.keys())}")
    
    remote_func = CPU_FUNCTION_REGISTRY[function_name]
    refs = [remote_func.remote(agent_data, *args, **kwargs) for agent_data in agent_data_list]
    return ray.get(refs)


def execute_parallel_gpu(function_name: str, agent_data_list, *args, **kwargs):
    """
    Execute a GPU-bound function in parallel for multiple agents.
    
    Args:
        function_name: Name of the function to execute (e.g., 'post_content')
        agent_data_list: List of AgentData instances
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        List of results in the same order as agent_data_list
    
    Raises:
        ValueError: If function_name is not a registered GPU function
    """
    if not RAY_AVAILABLE:
        # Fallback to sequential execution
        func = getattr(agent_llm_functions, function_name)
        return [func(agent_data, *args, **kwargs) for agent_data in agent_data_list]
    
    if function_name not in GPU_FUNCTION_REGISTRY:
        raise ValueError(f"Unknown GPU function: {function_name}. Available: {list(GPU_FUNCTION_REGISTRY.keys())}")
    
    remote_func = GPU_FUNCTION_REGISTRY[function_name]
    refs = [remote_func.remote(agent_data, *args, **kwargs) for agent_data in agent_data_list]
    return ray.get(refs)


def init_ray(num_cpus=None, num_gpus=None, **kwargs):
    """
    Initialize Ray with optional configuration.
    
    Args:
        num_cpus: Number of CPU cores to use (None = auto-detect)
        num_gpus: Number of GPUs to use (None = auto-detect)
        **kwargs: Additional Ray initialization parameters
    
    Returns:
        True if Ray was initialized, False if already initialized or not available
    """
    if not RAY_AVAILABLE:
        logger.warning("Ray is not available. Install with: pip install ray")
        return False
    
    if ray.is_initialized():
        logger.info("Ray is already initialized")
        return False
    
    init_kwargs = {}
    if num_cpus is not None:
        init_kwargs['num_cpus'] = num_cpus
    if num_gpus is not None:
        init_kwargs['num_gpus'] = num_gpus
    
    init_kwargs.update(kwargs)
    
    ray.init(**init_kwargs)
    logger.info(f"Ray initialized with {ray.available_resources()}")
    
    # Register functions after Ray is initialized
    _register_functions()
    
    return True


def shutdown_ray():
    """Shutdown Ray if it's running."""
    if RAY_AVAILABLE and ray.is_initialized():
        ray.shutdown()
        logger.info("Ray shutdown complete")
        return True
    return False


# Export public API - High-level utilities for users
__all__ = [
    # Ray control
    'RAY_AVAILABLE',
    'init_ray',
    'shutdown_ray',
    # High-level parallel execution
    'execute_parallel_cpu',
    'execute_parallel_gpu',
]

# Note: Low-level remote functions (cpu_*, gpu_*) are internal and accessed
# via the function registries. Users should use execute_parallel_* functions.
# Advanced users can access remote functions directly if needed via the module.
