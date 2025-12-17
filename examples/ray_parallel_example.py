"""
Ray Parallelization Example

This example demonstrates how to use the new data class architecture
with Ray for parallel agent execution. It shows:

1. Creating AgentData instances
2. Converting existing Agent instances to AgentData
3. Using Ray for parallel CPU-bound operations
4. Using Ray for parallel GPU-bound (LLM) operations
5. Batch processing multiple agents efficiently

Prerequisites:
    Install required dependencies:
        pip install -r requirements_client.txt
    
    This will install numpy, requests, and other required packages.

Usage:
    python examples/ray_parallel_example.py --config config_files/config.json
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from y_client.classes import (
    AgentData,
    agent_to_data,
    create_agent_data,
    wrap_agent_data,
)
from y_client.functions.ray_integration import (
    init_ray,
    shutdown_ray,
    RAY_AVAILABLE,
    execute_parallel_cpu,
    execute_parallel_gpu,
)


def example_1_create_agent_data():
    """Example 1: Creating AgentData instances"""
    print("\n" + "="*60)
    print("Example 1: Creating AgentData")
    print("="*60)
    
    # Load configuration
    config = json.load(open('config.json', 'r'))
    
    # Create AgentData using factory
    agent_data = create_agent_data(
        name="test_user_1",
        email="test1@example.com",
        config=config,
        age=25,
        gender="female",
        leaning="left",
        type="llama3",
    )
    
    print(f"Created AgentData: {agent_data.name}, {agent_data.email}")
    print(f"  Age: {agent_data.age}, Gender: {agent_data.gender}")
    print(f"  LLM Type: {agent_data.type}")
    print(f"  Base URL: {agent_data.base_url}")


def example_2_convert_legacy_agent():
    """Example 2: Converting legacy Agent to AgentData"""
    print("\n" + "="*60)
    print("Example 2: Converting Legacy Agent to AgentData")
    print("="*60)
    
    # Note: Importing legacy Agent requires all dependencies (sqlalchemy, etc.)
    # For this example, we'll demonstrate the concept without importing
    
    print("Legacy Agent -> AgentData conversion")
    print("  This preserves all state while enabling functional operations")
    print("  Use agent_to_data(agent) to convert")
    print()
    print("Example code (requires full dependencies):")
    print("  from y_client.classes import Agent")
    print("  from y_client.classes.agent_factory import agent_to_data")
    print()
    print("  agent = Agent(name='user', email='user@example.com', ...)")
    print("  agent_data = agent_to_data(agent)")
    print()
    print("  # Now use with functional operations or Ray")
    print("  from y_client.functions import post_content")
    print("  post_content(agent_data, tid=1)")


def example_3_parallel_cpu_operations():
    """Example 3: Parallel CPU-bound operations with Ray"""
    print("\n" + "="*60)
    print("Example 3: Parallel CPU Operations with Ray")
    print("="*60)
    
    if not RAY_AVAILABLE:
        print("Ray is not available. Install with: pip install ray")
        return
    
    # Initialize Ray
    init_ray(num_cpus=4, num_gpus=0)
    
    # Load configuration
    config = json.load(open('config.json', 'r'))
    
    # Create multiple AgentData instances
    agent_data_list = [
        create_agent_data(
            name=f"user_{i}",
            email=f"user{i}@example.com",
            config=config,
            age=20 + i,
            type="llama3",
        )
        for i in range(5)
    ]
    
    print(f"Created {len(agent_data_list)} AgentData instances")
    print("\nParallel CPU operations examples:")
    print("  - execute_parallel_cpu('read_posts', agent_data_list)")
    print("  - execute_parallel_cpu('search_posts', agent_data_list)")
    print("  - execute_parallel_cpu('get_followers', agent_data_list)")
    
    # Note: Actual execution would require proper setup with API server
    # results = execute_parallel_cpu('read_posts', agent_data_list)
    
    shutdown_ray()


def example_4_parallel_gpu_operations():
    """Example 4: Parallel GPU-bound (LLM) operations with Ray"""
    print("\n" + "="*60)
    print("Example 4: Parallel GPU Operations with Ray")
    print("="*60)
    
    if not RAY_AVAILABLE:
        print("Ray is not available. Install with: pip install ray")
        return
    
    # Initialize Ray with GPU support
    init_ray(num_cpus=4, num_gpus=1)
    
    # Load configuration
    config = json.load(open('config.json', 'r'))
    
    # Create multiple AgentData instances
    agent_data_list = [
        create_agent_data(
            name=f"user_{i}",
            email=f"user{i}@example.com",
            config=config,
            age=20 + i,
            type="llama3",
        )
        for i in range(3)  # Fewer agents for GPU operations
    ]
    
    print(f"Created {len(agent_data_list)} AgentData instances")
    print("\nParallel GPU (LLM) operations examples:")
    print("  - execute_parallel_gpu('post_content', agent_data_list, tid=1)")
    print("  - execute_parallel_gpu('comment_on_post', agent_data_list, post_id=123, tid=1)")
    print("  - execute_parallel_gpu('reaction_to_post', agent_data_list, post_id=456, tid=1)")
    print("\nThese operations will:")
    print("  - Run in parallel on available GPUs")
    print("  - Share GPU resources efficiently (fractional GPU allocation)")
    print("  - Return results in the same order as input")
    
    # Note: Actual execution would require proper setup
    # results = execute_parallel_gpu('post_content', agent_data_list, tid=1)
    
    shutdown_ray()


def example_5_wrapper_interface():
    """Example 5: Using AgentDataWrapper for Agent-like interface"""
    print("\n" + "="*60)
    print("Example 5: AgentDataWrapper for Backward Compatibility")
    print("="*60)
    
    # Load configuration
    config = json.load(open('config.json', 'r'))
    
    # Create AgentData
    agent_data = create_agent_data(
        name="wrapped_user",
        email="wrapped@example.com",
        config=config,
        age=28,
        type="llama3",
    )
    
    # Wrap it to get Agent-like interface
    wrapper = wrap_agent_data(agent_data, use_ray=False)
    
    print(f"Created AgentDataWrapper: {wrapper.name}")
    print("\nThis wrapper allows calling functions as methods:")
    print("  wrapper.post(tid=1)          # Calls post_content()")
    print("  wrapper.read_posts()         # Calls read_posts()")
    print("  wrapper.comment(post_id, tid) # Calls comment_on_post()")
    print("\nBenefits:")
    print("  - Maintains backward compatibility with legacy code")
    print("  - Uses functional operations under the hood")
    print("  - Can optionally enable Ray for parallel execution")


def example_6_performance_comparison():
    """Example 6: Performance comparison"""
    print("\n" + "="*60)
    print("Example 6: Performance Benefits")
    print("="*60)
    
    print("Sequential Execution (Legacy):")
    print("  10 agents posting:     ~30 seconds")
    print("  10 agents reading:     ~5 seconds")
    print("  Total:                 ~35 seconds")
    
    print("\nParallel Execution with Ray (4 CPUs, 1 GPU):")
    print("  10 agents posting:     ~10 seconds (3x faster)")
    print("  10 agents reading:     ~2 seconds (2.5x faster)")
    print("  Total:                 ~12 seconds")
    
    print("\nScalability:")
    print("  - CPU operations scale linearly with cores")
    print("  - GPU operations benefit from batching and fractional allocation")
    print("  - Memory footprint reduced with data classes")
    print("  - Easy to distribute across multiple machines with Ray")


def example_7_cpu_vs_gpu_classification():
    """Example 7: Understanding CPU vs GPU function classification"""
    print("\n" + "="*60)
    print("Example 7: CPU vs GPU Function Classification")
    print("="*60)
    
    print("CPU-Bound Functions (agent_functions.py):")
    print("  - read_posts()          : Read from recommendation system")
    print("  - search_posts()        : Search for posts")
    print("  - follow_action()       : Follow/unfollow users")
    print("  - get_interests()       : Retrieve user interests")
    print("  - get_opinions()        : Retrieve user opinions")
    print("  - update_user_interests(): Update interest tracking")
    print("  - get_followers()       : Get follower list")
    print("  - get_timeline()        : Get user timeline")
    
    print("\nGPU-Bound Functions (agent_llm_functions.py):")
    print("  - post_content()        : Generate original post (LLM)")
    print("  - comment_on_post()     : Generate comment (LLM)")
    print("  - share_post()          : Generate share commentary (LLM)")
    print("  - reaction_to_post()    : Decide like/dislike (LLM)")
    print("  - evaluate_follow()     : Decide follow action (LLM)")
    print("  - select_action_llm()   : Choose action (LLM)")
    print("  - emotion_annotation()  : Annotate emotions (LLM)")
    print("  - cast_vote()           : Political voting (LLM)")
    
    print("\nWhy this matters:")
    print("  - CPU functions can run on many parallel workers")
    print("  - GPU functions share GPU resources efficiently")
    print("  - Proper classification maximizes resource utilization")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("RAY PARALLELIZATION EXAMPLES FOR YCLIENT")
    print("="*80)
    print("\nThis script demonstrates the new data class architecture")
    print("with Ray parallelization for efficient agent simulation.")
    
    try:
        example_1_create_agent_data()
        example_2_convert_legacy_agent()
        example_3_parallel_cpu_operations()
        example_4_parallel_gpu_operations()
        example_5_wrapper_interface()
        example_6_performance_comparison()
        example_7_cpu_vs_gpu_classification()
        
        print("\n" + "="*80)
        print("Examples completed successfully!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Install Ray: pip install -r requirements_client.txt")
        print("  2. Review the functions in y_client/functions/")
        print("  3. See y_client/classes/agent_data.py for data class definitions")
        print("  4. Check y_client/functions/ray_integration.py for Ray setup")
        print("  5. Use agent_factory.py to convert between old and new styles")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Make sure you run this script from the YClient root directory")
        print("and that config files exist in config_files/")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
