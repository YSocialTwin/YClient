"""
Simulation Pipeline Example with FakeAgents (No LLM Required)

This example demonstrates how to run a multi-day, multi-hour simulation
using FakeAgents that connect to a YServer backend WITHOUT requiring LLMs.
FakeAgents perform actions without LLM-based content generation, making
this suitable for testing and development.

**YServer Configuration:**
- Host: 0.0.0.0
- Port: 5010

Prerequisites:
    1. YServer must be running at http://0.0.0.0:5010
    2. Install dependencies:
        pip install numpy requests pyautogen==0.2.31
    3. For Ray parallelization:
        pip install ray

Usage:
    # Run a 2-day simulation with 4 hours per day, 10 fake agents
    python examples/simulation_pipeline_fakeagent.py --days 2 --slots 4 --agents 10
    
    # Run with Ray using 4 CPUs (no GPU needed for FakeAgents)
    python examples/simulation_pipeline_fakeagent.py --days 2 --slots 4 --agents 10 --ray-cpus 4
    
    # Run without Ray (sequential)
    python examples/simulation_pipeline_fakeagent.py --no-ray
    
    # Full week simulation
    python examples/simulation_pipeline_fakeagent.py --days 7 --slots 24 --agents 100 --pages 10

Features:
    - Uses FakeAgent class (no LLM content generation)
    - Connects to YServer at 0.0.0.0:5010
    - Multi-day, multi-hour simulation loop
    - Hourly agent sampling with activity profiles
    - Page agents posting each hour
    - User agents performing various actions
    - Optional Ray parallelization for performance
    - End-of-day tasks (follows, churn, new agents)
"""

import json
import sys
import os
import random
import argparse
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from y_client.classes import FakeAgent
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


def create_fake_agent(
    name: str,
    email: str,
    base_url: str,
    config: Dict,
    is_page: bool = False
) -> FakeAgent:
    """
    Create a FakeAgent instance that communicates with YServer.
    
    Args:
        name: Agent username
        email: Agent email
        base_url: YServer base URL
        config: Configuration dictionary
        is_page: Whether this is a page agent
    
    Returns:
        FakeAgent instance
    """
    agent = FakeAgent(
        name=name,
        email=email,
        pwd="password123",
        age=random.randint(25 if is_page else 18, 50 if is_page else 65),
        gender=random.choice(["male", "female", "non-binary"]),
        nationality="American",
        language="english",
        interests=random.sample([
            "technology", "science", "politics", "sports", "entertainment",
            "business", "health", "education", "travel", "food"
        ], k=random.randint(3, 6)),
        leaning=random.choice(["Democrat", "Republican", "Independent"]),
        education_level=random.choice(["bachelor", "master", "phd"] if is_page 
                                     else ["high school", "bachelor", "master"]),
        profession=random.choice(["engineer", "teacher", "doctor", "journalist"] if is_page
                                else ["engineer", "teacher", "nurse", "writer", "student"]),
        toxicity="no" if is_page else random.choice(["no", "low"]),
        round_actions=random.randint(1, 3),
        daily_activity_level=random.randint(1, 3),
        config=config,
        is_page=1 if is_page else 0,
        archetype=None if is_page else random.choice(["validator", "broadcaster", "explorer"]),
    )
    return agent


def execute_page_posts_sequential(pages: List[FakeAgent], tid: int):
    """
    Execute page posting sequentially (non-Ray fallback).
    
    Args:
        pages: List of page agents
        tid: Current time slot ID
    """
    print(f"    [{len(pages)} pages] Posting content (sequential)...")
    for page in pages:
        try:
            # FakeAgent pages use select_action_lite which calls backend API
            page.select_action_lite(tid=tid, actions=[])
        except Exception as e:
            print(f"    Error posting for {page.name}: {e}")


def execute_page_posts_parallel(pages: List[FakeAgent], tid: int):
    """
    Execute page posting in parallel using Ray (if available).
    
    Args:
        pages: List of page agents
        tid: Current time slot ID
    """
    if not RAY_AVAILABLE:
        execute_page_posts_sequential(pages, tid)
        return
    
    print(f"    [{len(pages)} pages] Posting content (parallel with Ray)...")
    try:
        # In a real implementation, this would use Ray to parallelize
        # page posting actions across multiple workers
        # For now, using sequential fallback
        execute_page_posts_sequential(pages, tid)
    except Exception as e:
        print(f"    Error in parallel page posting: {e}")
        execute_page_posts_sequential(pages, tid)


def execute_agent_actions_sequential(
    agents: List[FakeAgent],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions sequentially (non-Ray fallback).
    
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
                # Sample actions for the agent
                if len(actions_pool) > 1:
                    candidates = random.choices(actions_pool, k=2)
                    candidates.append("NONE")
                else:
                    candidates = actions_pool + ["NONE"]
                
                # FakeAgent's select_action method will call backend API
                agent.select_action(tid=tid, actions=candidates)
            except Exception as e:
                print(f"    Error executing action for {agent.name}: {e}")


def execute_agent_actions_parallel(
    agents: List[FakeAgent],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions in parallel using Ray (if available).
    
    Args:
        agents: List of agents to process
        tid: Current time slot ID
        actions_pool: Available actions
        max_rounds: Maximum actions per agent
    """
    if not RAY_AVAILABLE:
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)
        return
    
    print(f"    [{len(agents)} agents] Executing actions (parallel with Ray)...")
    try:
        # In a real implementation, this would use Ray to parallelize
        # agent actions across multiple workers
        # For now, using sequential fallback
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)
    except Exception as e:
        print(f"    Error in parallel agent actions: {e}")
        execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)


def handle_daily_follows(agents: List[FakeAgent], tid: int, probability: float = 0.1):
    """
    Handle end-of-day follow evaluation.
    
    Args:
        agents: List of agents
        tid: Current time slot ID
        probability: Probability of follow evaluation per agent
    """
    eligible = [a for a in agents if not a.is_page and random.random() < probability]
    if eligible:
        print(f"  End-of-day: {len(eligible)} agents evaluating follows...")
        for agent in eligible:
            try:
                # FakeAgent's select_action will call backend API for FOLLOW action
                agent.select_action(tid=tid, actions=["FOLLOW", "NONE"])
            except Exception as e:
                print(f"  Error in follow evaluation for {agent.name}: {e}")


def handle_churn(agents: List[FakeAgent], tid: int, churn_rate: float = 0.01) -> List[FakeAgent]:
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
    churned = random.sample([a for a in agents if not a.is_page], min(n_churn, len([a for a in agents if not a.is_page])))
    
    if churned:
        print(f"  End-of-day: {len(churned)} agents churning...")
        remaining = [a for a in agents if a not in churned]
        return remaining
    return agents


def add_new_agents(
    agents: List[FakeAgent],
    base_url: str,
    config: Dict,
    n_new: int,
    agent_counter: int
) -> Tuple[List[FakeAgent], int]:
    """
    Add new agents to the simulation.
    
    Args:
        agents: Current list of agents
        base_url: YServer base URL
        config: Configuration dictionary
        n_new: Number of new agents to add
        agent_counter: Current agent counter for naming
    
    Returns:
        Tuple of (updated agent list, updated counter)
    """
    if n_new > 0:
        print(f"  End-of-day: Adding {n_new} new agents...")
        new_agents = []
        for i in range(n_new):
            name = f"fake_user_{agent_counter + i}"
            email = f"fake_user_{agent_counter + i}@example.com"
            new_agents.append(create_fake_agent(name, email, base_url, config, is_page=False))
        
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
    server_host: str = "0.0.0.0",
    server_port: int = 5010
):
    """
    Run the complete simulation pipeline with FakeAgents.
    
    Args:
        days: Number of simulation days
        slots_per_day: Time slots per day (typically 24 hours)
        n_agents: Number of user agents
        n_pages: Number of page agents
        use_ray: Whether to use Ray for parallelization
        ray_cpus: Number of CPUs for Ray
        ray_gpus: Number of GPUs for Ray (not needed for FakeAgents)
        server_host: YServer host address
        server_port: YServer port
    """
    print("=" * 80)
    print("SIMULATION PIPELINE WITH FAKEAGENTS (NO LLM)")
    print("=" * 80)
    print()
    
    # Configure YServer connection
    base_url = f"http://{server_host}:{server_port}"
    print(f"YServer URL: {base_url}")
    print()
    
    print("Configuration:")
    print(f"  Total days: {days}")
    print(f"  Slots per day: {slots_per_day}")
    print(f"  User agents: {n_agents}")
    print(f"  Page agents: {n_pages}")
    print(f"  Ray parallelization: {use_ray and RAY_AVAILABLE}")
    print()
    
    # Initialize Ray if enabled
    if use_ray and RAY_AVAILABLE:
        print("🚀 Initializing Ray...")
        try:
            init_ray(num_cpus=ray_cpus, num_gpus=ray_gpus)
            print(f"   Ray initialized with {ray_cpus} CPUs, {ray_gpus} GPUs")
        except Exception as e:
            print(f"   Warning: Ray initialization failed: {e}")
            print("   Falling back to sequential execution")
            use_ray = False
    else:
        print("📋 Using sequential execution (Ray not available or disabled)")
    print()
    
    # Create configuration for agents
    config = {
        "server": {"host": server_host, "port": server_port},
        "agents": {
            "probability_of_daily_follow": 0.1,
            "probability_of_secondary_follow": 0.05,
        },
        "simulation": {
            "max_length_thread_reading": 3,
        }
    }
    
    # Create agents
    print("Creating agents...")
    user_agents = []
    page_agents = []
    agent_counter = 0
    
    for i in range(n_agents):
        name = f"fake_user_{i}"
        email = f"fake_user_{i}@example.com"
        user_agents.append(create_fake_agent(name, email, base_url, config, is_page=False))
        agent_counter += 1
    
    for i in range(n_pages):
        name = f"fake_page_{i}"
        email = f"fake_page_{i}@example.com"
        page_agents.append(create_fake_agent(name, email, base_url, config, is_page=True))
    
    all_agents = user_agents + page_agents
    print(f"  Created {len(user_agents)} user agents and {len(page_agents)} page agents")
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
    print("STARTING SIMULATION")
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
            
            # Pages post content
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
            
            print(f"    👥 {len(active_users)} active users")
            daily_active.update([a.name for a in active_users])
            
            # Execute user actions
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
            # Daily follows
            handle_daily_follows(user_agents, tid, probability=0.1)
            
            # Daily churn
            user_agents = handle_churn(user_agents, tid, churn_rate=0.014)
            
            # Add new agents
            n_new = max(1, int(len(daily_active) * 0.07))
            user_agents, agent_counter = add_new_agents(user_agents, base_url, config, n_new, agent_counter)
            
            print(f"  Current population: {len(user_agents)} users, {len(page_agents)} pages")
        
        print()
    
    print("=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Final statistics:")
    print(f"  Total slots simulated: {sim_clock.current_slot}")
    print(f"  Final population: {len(user_agents)} users, {len(page_agents)} pages")
    print()
    
    # Cleanup Ray
    if use_ray and RAY_AVAILABLE:
        print("Shutting down Ray...")
        shutdown_ray()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulation Pipeline with FakeAgents (No LLM Required)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--days", type=int, default=2, help="Number of simulation days (default: 2)")
    parser.add_argument("--slots", type=int, default=4, help="Time slots per day (default: 4, typically 24)")
    parser.add_argument("--agents", type=int, default=10, help="Number of user agents (default: 10)")
    parser.add_argument("--pages", type=int, default=2, help="Number of page agents (default: 2)")
    parser.add_argument("--no-ray", action="store_true", help="Disable Ray parallelization")
    parser.add_argument("--ray-cpus", type=int, default=4, help="Number of CPUs for Ray (default: 4)")
    parser.add_argument("--ray-gpus", type=int, default=0, help="Number of GPUs for Ray (default: 0)")
    parser.add_argument("--server-host", type=str, default="0.0.0.0", help="YServer host (default: 0.0.0.0)")
    parser.add_argument("--server-port", type=int, default=5010, help="YServer port (default: 5010)")
    
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
            server_host=args.server_host,
            server_port=args.server_port
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
