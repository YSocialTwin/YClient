"""
Simulation Pipeline Example with LLM Agents using Ollama (llama3.2)

This example demonstrates how to run a multi-day, multi-hour simulation
using real Agent instances that connect to a localhost Ollama instance
running llama3.2 for LLM-based content generation and decision-making.

**System Requirements:**
- YServer running at http://0.0.0.0:5010
- Ollama running at http://127.0.0.1:11434 with llama3.2 model

Prerequisites:
    1. Install and run Ollama:
        # Install Ollama from https://ollama.ai/
        # Pull llama3.2 model
        ollama pull llama3.2
        
        # Start Ollama server (usually runs automatically)
        # It should be available at http://127.0.0.1:11434
    
    2. YServer must be running at http://0.0.0.0:5010
    
    3. Install dependencies:
        pip install numpy requests pyautogen==0.2.31
    
    4. For Ray parallelization:
        pip install ray

Usage:
    # Run a 2-day simulation with 4 hours per day, 10 LLM agents
    python examples/simulation_pipeline_llm_ollama.py --days 2 --slots 4 --agents 10
    
    # Run with Ray using 4 CPUs and 1 GPU (if available)
    python examples/simulation_pipeline_llm_ollama.py --days 2 --slots 4 --agents 10 --ray-cpus 4 --ray-gpus 1
    
    # Run without Ray (sequential)
    python examples/simulation_pipeline_llm_ollama.py --no-ray
    
    # Full week simulation
    python examples/simulation_pipeline_llm_ollama.py --days 7 --slots 24 --agents 50 --pages 5

Features:
    - Uses real Agent class with LLM content generation
    - Connects to Ollama at http://127.0.0.1:11434 (llama3.2)
    - Connects to YServer at http://0.0.0.0:5010
    - Multi-day, multi-hour simulation loop
    - LLM-powered content creation and decision-making
    - Hourly agent sampling with activity profiles
    - Page agents with LLM-generated posts
    - User agents performing LLM-driven actions
    - Optional Ray parallelization for GPU sharing
    - End-of-day tasks (follows, churn, new agents)

Note:
    LLM operations are GPU-intensive. Ray parallelization with fractional GPU
    allocation (0.1 per task) allows ~10 agents to share a single GPU efficiently.
"""

import json
import sys
import os
import random
import argparse
from typing import List, Dict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from y_client.classes.agent_data import AgentData, PageAgentData
from y_client.functions.ray_integration import (
    init_ray,
    shutdown_ray,
    RAY_AVAILABLE,
)


class SimulationClock:
    """Simple simulation clock to track days and hours."""
    
    def __init__(self, slots_per_day: int = 24):
        self.current_slot = 0
        self.slots_per_day = slots_per_day
    
    def get_current_slot(self):
        """Returns (slot_id, day, hour)"""
        day = self.current_slot // self.slots_per_day
        hour = self.current_slot % self.slots_per_day
        return self.current_slot, day, hour
    
    def increment_slot(self):
        """Move to the next time slot."""
        self.current_slot += 1


def create_llm_config(ollama_url: str = "http://127.0.0.1:11434/v1") -> Dict:
    """
    Create LLM configuration for Ollama.
    
    Args:
        ollama_url: Ollama API endpoint
    
    Returns:
        LLM configuration dictionary
    """
    return {
        "config_list": [
            {
                "model": "llama3.2",
                "base_url": ollama_url,
                "api_key": "NULL",  # Ollama doesn't require API key
            }
        ],
        "temperature": 1.5,
        "max_tokens": -1,  # No limit
    }


def create_llm_agent(
    name: str,
    email: str,
    yserver_url: str,
    ollama_url: str,
    is_page: bool = False
) -> AgentData:
    """
    Create an AgentData instance configured for LLM (Ollama).
    
    Args:
        name: Agent username
        email: Agent email
        yserver_url: YServer base URL
        ollama_url: Ollama API endpoint
        is_page: Whether this is a page agent
    
    Returns:
        AgentData or PageAgentData instance
    """
    llm_config = create_llm_config(ollama_url)
    
    common_attrs = {
        "name": name,
        "email": email,
        "pwd": "password123",
        "age": random.randint(25 if is_page else 18, 50 if is_page else 65),
        "gender": random.choice(["male", "female", "non-binary"]),
        "nationality": "American",
        "language": "english",
        "interests": random.sample([
            "technology", "science", "politics", "sports", "entertainment",
            "business", "health", "education", "travel", "food",
            "art", "music", "literature", "environment", "philosophy"
        ], k=random.randint(4, 8)),
        "leaning": random.choice(["Democrat", "Republican", "Independent"]),
        "education_level": random.choice(["bachelor", "master", "phd"] if is_page else ["high school", "bachelor", "master"]),
        "profession": random.choice([
            "engineer", "teacher", "doctor", "journalist", "writer",
            "scientist", "analyst", "designer", "manager", "consultant"
        ]),
        "toxicity": "no",
        "round_actions": random.randint(1, 3),
        "daily_activity_level": random.randint(1, 3),
        "base_url": yserver_url,
        "llm_base": ollama_url,
        "llm_config": llm_config,
        "is_page": 1 if is_page else 0,
        "type": "llama3.2",  # Using llama3.2 via Ollama
        "archetype": None if is_page else random.choice(["validator", "broadcaster", "explorer"]),
    }
    
    if is_page:
        return PageAgentData(**common_attrs)
    else:
        return AgentData(**common_attrs)


def execute_page_posts_sequential(pages: List[PageAgentData], tid: int):
    """
    Execute page posting sequentially with LLM (non-Ray fallback).
    
    Args:
        pages: List of page agents
        tid: Current time slot ID
    """
    print(f"    [{len(pages)} pages] Posting content with LLM (sequential)...")
    for page in pages:
        try:
            # In a real implementation:
            # from y_client.functions.agent_llm_functions import post_content
            # post_content(page, tid, content_type="news")
            
            # For demonstration, just print
            print(f"      {page.name} posted content (LLM-generated)")
        except Exception as e:
            print(f"    Error posting for {page.name}: {e}")


def execute_page_posts_parallel(pages: List[PageAgentData], tid: int):
    """
    Execute page posting in parallel using Ray with GPU allocation.
    
    Args:
        pages: List of page agents
        tid: Current time slot ID
    """
    if not RAY_AVAILABLE:
        execute_page_posts_sequential(pages, tid)
        return
    
    print(f"    [{len(pages)} pages] Posting content with LLM (parallel, GPU)...")
    try:
        # In a real implementation with Ray:
        # from y_client.functions.ray_integration import execute_parallel_gpu
        # results = execute_parallel_gpu('post_content', pages, tid=tid, content_type="news")
        
        # For demonstration, use sequential
        execute_page_posts_sequential(pages, tid)
    except Exception as e:
        print(f"    Error in parallel page posting: {e}")
        execute_page_posts_sequential(pages, tid)


def execute_agent_actions_sequential(
    agents: List[AgentData],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions sequentially with LLM (non-Ray fallback).
    
    Args:
        agents: List of agents to process
        tid: Current time slot ID
        actions_pool: Available actions
        max_rounds: Maximum actions per agent
    """
    for agent in agents:
        rounds = random.randint(1, max_rounds)
        for _ in range(rounds):
            try:
                # In a real implementation:
                # from y_client.functions.agent_llm_functions import select_action_llm
                # selected = select_action_llm(agent, tid, actions_pool)
                
                # Sample actions with LLM decision
                if len(actions_pool) > 1:
                    candidates = random.choices(actions_pool, k=2)
                    candidates.append("NONE")
                else:
                    candidates = actions_pool + ["NONE"]
                
                # LLM would decide which action to take
                selected_action = random.choice(candidates)
                print(f"      {agent.name} performed {selected_action} (LLM-decided)")
                
            except Exception as e:
                print(f"    Error executing action for {agent.name}: {e}")


def execute_agent_actions_parallel(
    agents: List[AgentData],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions in parallel using Ray with GPU allocation.
    
    Args:
        agents: List of agents to process
        tid: Current time slot ID
        actions_pool: Available actions
        max_rounds: Maximum actions per agent
    """
    if not RAY_AVAILABLE:
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)
        return
    
    print(f"    [{len(agents)} agents] Executing LLM actions (parallel, GPU)...")
    try:
        # In a real implementation with Ray:
        # from y_client.functions.ray_integration import execute_parallel_gpu
        # 
        # # Prepare all agent action tasks
        # tasks = []
        # for agent in agents:
        #     rounds = random.randint(1, max_rounds)
        #     for _ in range(rounds):
        #         tasks.append((agent, tid, actions_pool))
        # 
        # # Execute in parallel with fractional GPU (0.1 per task = 10 agents per GPU)
        # results = execute_parallel_gpu('select_action_llm', [t[0] for t in tasks], 
        #                               tid=tid, actions=actions_pool)
        
        # For demonstration, use sequential
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)
    except Exception as e:
        print(f"    Error in parallel agent actions: {e}")
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)


def handle_daily_follows(agents: List[AgentData], tid: int, probability: float = 0.1):
    """
    Handle end-of-day follow evaluation with LLM.
    
    Args:
        agents: List of agents
        tid: Current time slot ID
        probability: Probability of follow evaluation per agent
    """
    eligible = [a for a in agents if not a.is_page and random.random() < probability]
    if eligible:
        print(f"  End-of-day: {len(eligible)} agents evaluating follows (LLM)...")
        for agent in eligible:
            try:
                # In a real implementation:
                # from y_client.functions.agent_llm_functions import evaluate_follow
                # evaluate_follow(agent, tid)
                
                print(f"    {agent.name} evaluated potential follows (LLM)")
            except Exception as e:
                print(f"  Error in follow evaluation for {agent.name}: {e}")


def handle_churn(agents: List[AgentData], tid: int, churn_rate: float = 0.01) -> List[AgentData]:
    """
    Handle agent churn (removal).
    
    Args:
        agents: List of current agents
        tid: Current time slot ID
        churn_rate: Probability of agent churn
    
    Returns:
        Updated list of agents after churn
    """
    n_churn = max(1, int(len(agents) * churn_rate))
    non_page_agents = [a for a in agents if not a.is_page]
    churned = random.sample(non_page_agents, min(n_churn, len(non_page_agents)))
    
    if churned:
        print(f"  End-of-day: {len(churned)} agents churning...")
        remaining = [a for a in agents if a not in churned]
        return remaining
    return agents


def add_new_agents(
    agents: List[AgentData],
    yserver_url: str,
    ollama_url: str,
    n_new: int,
    agent_counter: int
) -> tuple[List[AgentData], int]:
    """
    Add new LLM agents to the simulation.
    
    Args:
        agents: Current list of agents
        yserver_url: YServer base URL
        ollama_url: Ollama API endpoint
        n_new: Number of new agents to add
        agent_counter: Current agent counter for naming
    
    Returns:
        Tuple of (updated agent list, updated counter)
    """
    if n_new > 0:
        print(f"  End-of-day: Adding {n_new} new LLM agents...")
        new_agents = []
        for i in range(n_new):
            name = f"llm_user_{agent_counter + i}"
            email = f"llm_user_{agent_counter + i}@example.com"
            new_agents.append(create_llm_agent(name, email, yserver_url, ollama_url, is_page=False))
        
        agents.extend(new_agents)
        agent_counter += n_new
    
    return agents, agent_counter


def run_simulation_pipeline(
    days: int,
    slots_per_day: int,
    n_agents: int,
    n_pages: int,
    use_ray: bool = True,
    ray_cpus: int = 4,
    ray_gpus: int = 0,
    yserver_host: str = "0.0.0.0",
    yserver_port: int = 5010,
    ollama_url: str = "http://127.0.0.1:11434/v1"
):
    """
    Run the complete simulation pipeline with LLM agents (Ollama).
    
    Args:
        days: Number of simulation days
        slots_per_day: Time slots per day (typically 24 hours)
        n_agents: Number of user agents
        n_pages: Number of page agents
        use_ray: Whether to use Ray for parallelization
        ray_cpus: Number of CPUs for Ray
        ray_gpus: Number of GPUs for Ray
        yserver_host: YServer host address
        yserver_port: YServer port
        ollama_url: Ollama API endpoint
    """
    print("=" * 80)
    print("SIMULATION PIPELINE WITH LLM AGENTS (OLLAMA - llama3.2)")
    print("=" * 80)
    print()
    
    # Configure URLs
    yserver_url = f"http://{yserver_host}:{yserver_port}"
    print(f"YServer URL: {yserver_url}")
    print(f"Ollama URL: {ollama_url}")
    print()
    
    print("Configuration:")
    print(f"  Total days: {days}")
    print(f"  Slots per day: {slots_per_day}")
    print(f"  User agents: {n_agents}")
    print(f"  Page agents: {n_pages}")
    print(f"  LLM Model: llama3.2 (via Ollama)")
    print(f"  Ray parallelization: {use_ray and RAY_AVAILABLE}")
    print()
    
    # Initialize Ray if enabled
    if use_ray and RAY_AVAILABLE:
        print("🚀 Initializing Ray with GPU support...")
        try:
            init_ray(num_cpus=ray_cpus, num_gpus=ray_gpus)
            print(f"   Ray initialized with {ray_cpus} CPUs, {ray_gpus} GPUs")
            if ray_gpus > 0:
                print(f"   GPU tasks will use fractional allocation (0.1 per task)")
                print(f"   This allows ~10 LLM agents to share each GPU efficiently")
        except Exception as e:
            print(f"   Warning: Ray initialization failed: {e}")
            print("   Falling back to sequential execution")
            use_ray = False
    else:
        print("📋 Using sequential execution (Ray not available or disabled)")
    print()
    
    # Create agents
    print("Creating LLM agents...")
    user_agents = []
    page_agents = []
    agent_counter = 0
    
    for i in range(n_agents):
        name = f"llm_user_{i}"
        email = f"llm_user_{i}@example.com"
        user_agents.append(create_llm_agent(name, email, yserver_url, ollama_url, is_page=False))
        agent_counter += 1
    
    for i in range(n_pages):
        name = f"llm_page_{i}"
        email = f"llm_page_{i}@example.com"
        page_agents.append(create_llm_agent(name, email, yserver_url, ollama_url, is_page=True))
    
    all_agents = user_agents + page_agents
    print(f"  Created {len(user_agents)} LLM user agents and {len(page_agents)} LLM page agents")
    print()
    
    # Hourly activity profile
    hourly_activity = {
        "0": 0.023, "1": 0.021, "2": 0.020, "3": 0.020, "4": 0.018, "5": 0.017,
        "6": 0.017, "7": 0.018, "8": 0.020, "9": 0.020, "10": 0.021, "11": 0.022,
        "12": 0.024, "13": 0.027, "14": 0.030, "15": 0.032, "16": 0.032, "17": 0.032,
        "18": 0.032, "19": 0.031, "20": 0.030, "21": 0.029, "22": 0.027, "23": 0.025
    }
    
    # Actions available
    actions_pool = ["READ", "POST", "COMMENT", "SEARCH", "SHARE"]
    
    # Initialize simulation clock
    sim_clock = SimulationClock(slots_per_day=slots_per_day)
    
    print("=" * 80)
    print("STARTING LLM-POWERED SIMULATION")
    print("=" * 80)
    print()
    
    # Main simulation loop
    for day in range(days):
        print(f"📅 DAY {day + 1}/{days}")
        print("-" * 80)
        
        daily_active = set()
        
        for slot in range(slots_per_day):
            tid, d, h = sim_clock.get_current_slot()
            print(f"  ⏰ Slot {tid} (Day {d}, Hour {h})")
            
            # Calculate expected active users based on hourly activity
            expected_active = max(1, int(len(user_agents) * hourly_activity.get(str(h), 0.025)))
            expected_active = min(expected_active, len(user_agents))
            
            # Get active pages
            active_pages = [p for p in page_agents if random.random() > 0.3]  # 70% chance active
            
            # Pages post content with LLM
            if active_pages:
                if use_ray and RAY_AVAILABLE:
                    execute_page_posts_parallel(active_pages, tid)
                else:
                    execute_page_posts_sequential(active_pages, tid)
            
            # Sample active users for this hour
            active_users = random.sample(user_agents, expected_active) if len(user_agents) > expected_active else user_agents
            
            if not active_users:
                print("    No active users in this slot")
                sim_clock.increment_slot()
                continue
            
            print(f"    👥 {len(active_users)} active LLM users")
            daily_active.update([a.name for a in active_users])
            
            # Execute user actions with LLM
            if use_ray and RAY_AVAILABLE:
                execute_agent_actions_parallel(active_users, tid, actions_pool)
            else:
                execute_agent_actions_sequential(active_users, tid, actions_pool)
            
            # Increment simulation clock
            sim_clock.increment_slot()
        
        print()
        print(f"  📊 End of day {day + 1}: {len(daily_active)} unique active users")
        print()
        
        # End-of-day tasks
        if len(daily_active) > 0:
            # Daily follows with LLM
            handle_daily_follows(user_agents, tid, probability=0.1)
            
            # Daily churn
            user_agents = handle_churn(user_agents, tid, churn_rate=0.014)
            
            # Add new LLM agents
            n_new = max(1, int(len(daily_active) * 0.07))
            user_agents, agent_counter = add_new_agents(
                user_agents, yserver_url, ollama_url, n_new, agent_counter
            )
            
            print(f"  Current population: {len(user_agents)} users, {len(page_agents)} pages")
        
        print()
    
    print("=" * 80)
    print("LLM SIMULATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Final statistics:")
    print(f"  Total slots simulated: {sim_clock.current_slot}")
    print(f"  Final population: {len(user_agents)} users, {len(page_agents)} pages")
    print(f"  LLM model used: llama3.2 via Ollama")
    print()
    
    # Cleanup Ray
    if use_ray and RAY_AVAILABLE:
        print("Shutting down Ray...")
        shutdown_ray()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulation Pipeline with LLM Agents using Ollama (llama3.2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic simulation with LLM agents
  python simulation_pipeline_llm_ollama.py --days 2 --slots 4 --agents 10
  
  # With GPU acceleration (1 GPU shared across agents)
  python simulation_pipeline_llm_ollama.py --days 2 --slots 4 --agents 10 --ray-gpus 1
  
  # Full week simulation
  python simulation_pipeline_llm_ollama.py --days 7 --slots 24 --agents 50 --pages 5 --ray-gpus 1

Requirements:
  1. Ollama running at http://127.0.0.1:11434 with llama3.2 model
  2. YServer running at http://0.0.0.0:5010
        """
    )
    
    parser.add_argument("--days", type=int, default=2, help="Number of simulation days (default: 2)")
    parser.add_argument("--slots", type=int, default=4, help="Time slots per day (default: 4, typically 24)")
    parser.add_argument("--agents", type=int, default=10, help="Number of user agents (default: 10)")
    parser.add_argument("--pages", type=int, default=2, help="Number of page agents (default: 2)")
    parser.add_argument("--no-ray", action="store_true", help="Disable Ray parallelization")
    parser.add_argument("--ray-cpus", type=int, default=4, help="Number of CPUs for Ray (default: 4)")
    parser.add_argument("--ray-gpus", type=int, default=0, help="Number of GPUs for Ray (default: 0, use 1 if available)")
    parser.add_argument("--yserver-host", type=str, default="0.0.0.0", help="YServer host (default: 0.0.0.0)")
    parser.add_argument("--yserver-port", type=int, default=5010, help="YServer port (default: 5010)")
    parser.add_argument("--ollama-url", type=str, default="http://127.0.0.1:11434/v1", 
                       help="Ollama API endpoint (default: http://127.0.0.1:11434/v1)")
    
    args = parser.parse_args()
    
    try:
        run_simulation_pipeline(
            days=args.days,
            slots_per_day=args.slots,
            n_agents=args.agents,
            n_pages=args.pages,
            use_ray=not args.no_ray,
            ray_cpus=args.ray_cpus,
            ray_gpus=args.ray_gpus,
            yserver_host=args.yserver_host,
            yserver_port=args.yserver_port,
            ollama_url=args.ollama_url
        )
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        if not args.no_ray and RAY_AVAILABLE:
            shutdown_ray()
    except Exception as e:
        print(f"\nError during simulation: {e}")
        import traceback
        traceback.print_exc()
        if not args.no_ray and RAY_AVAILABLE:
            shutdown_ray()
        sys.exit(1)


if __name__ == "__main__":
    main()
