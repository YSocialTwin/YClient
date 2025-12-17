"""
Simulation Pipeline Example with Ray Parallelization

This example demonstrates how to run a multi-day, multi-hour simulation
using the new Ray-based architecture. It replicates the daily/hourly 
simulation pattern with parallel agent execution.

**IMPORTANT: This is a DEMONSTRATION of the simulation pattern.**
The actual LLM backend calls are mocked/commented out to allow running
without a full backend setup. In a real simulation:
1. Uncomment the actual function calls in execute_*_parallel functions
2. Ensure the YServer backend is running
3. Configure proper API endpoints in config.json

The simulation follows this pattern:
1. Daily loop: Iterate through simulation days
2. Hourly loop: Iterate through time slots within each day
3. Agent sampling: Select active agents for each hour based on activity profiles
4. Parallel execution: Process agent actions in parallel using Ray
5. End-of-day tasks: Handle follows, churn, new agents

Key Features Demonstrated:
- Multi-day, multi-hour simulation structure
- Hourly activity profiles for agents
- Page agents posting content
- User agents performing varied actions
- Ray parallelization for scalable execution
- Daily follow evaluation
- Agent churn and recruitment
- Proper simulation clock management

Prerequisites:
    Install required dependencies:
        pip install numpy requests pyautogen==0.2.31
    
    For Ray parallelization:
        pip install ray

Usage:
    # Run a 2-day simulation with 4 hours per day, 10 agents
    python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10
    
    # Run without Ray (sequential)
    python examples/simulation_pipeline_example.py --no-ray
    
    # Customize all parameters
    python examples/simulation_pipeline_example.py --days 3 --slots 24 --agents 50 --pages 5
    
    # Full day simulation (24 hours)
    python examples/simulation_pipeline_example.py --days 7 --slots 24 --agents 100 --pages 10

Real Simulation Integration:
    To integrate this pattern into a real simulation:
    
    1. **Setup Backend**: Ensure YServer is running with proper database
    
    2. **Configure Endpoints**: Update config.json with correct API URLs
    
    3. **Enable LLM Calls**: In the functions below, uncomment the actual
       LLM function calls (search for "In a real simulation with backend")
    
    4. **Add Database Tracking**: Integrate with Client_Execution table to
       track progress and handle completion status
    
    5. **Implement Real Churn**: Add actual agent removal and creation logic
    
    6. **Add Agent Saving**: Implement periodic agent state serialization
    
    Example integration:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Setup database connection
        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Track execution in database
        ce = session.query(Client_Execution).filter_by(client_id=cli_id).first()
        ce.elapsed_time += 1
        session.commit()
"""

import json
import sys
import os
import random
from typing import List, Dict, Set
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from y_client.classes.agent_data import AgentData, PageAgentData
from y_client.classes.agent_factory import create_agent_data
from y_client.functions.ray_integration import (
    init_ray,
    shutdown_ray,
    RAY_AVAILABLE,
    execute_parallel_cpu,
    execute_parallel_gpu,
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


def sample_agents_by_hour(
    all_agents: List[AgentData],
    hour: int,
    expected_active: int,
    hourly_activity: Dict[str, float]
) -> List[AgentData]:
    """
    Sample agents to be active in a given hour based on activity profiles.
    
    Args:
        all_agents: List of all available agents
        hour: Current hour (0-23)
        expected_active: Number of agents expected to be active
        hourly_activity: Dictionary mapping hour to activity probability
    
    Returns:
        List of sampled active agents
    """
    # Filter agents available at this hour (simplified - in real scenario
    # agents would have activity profiles)
    available_agents = [a for a in all_agents if not a.is_page]
    
    # Sample agents based on expected activity
    if len(available_agents) <= expected_active:
        return available_agents
    
    return random.sample(available_agents, expected_active)


def get_active_pages(page_agents: List[PageAgentData], hour: int) -> List[PageAgentData]:
    """
    Get pages that should be active at this hour.
    
    Args:
        page_agents: List of page agents
        hour: Current hour (0-23)
    
    Returns:
        List of active page agents
    """
    # Simplified: all pages active all the time
    # In real scenario, pages would have activity profiles
    return page_agents


def execute_agent_actions_sequential(
    agents: List[AgentData],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions sequentially (non-Ray fallback).
    
    NOTE: This is a simplified demonstration. In a real simulation,
    this would call actual LLM functions that interact with the backend.
    
    Args:
        agents: List of agents to process
        tid: Current time slot ID
        actions_pool: Available actions
        max_rounds: Maximum actions per agent
    """
    # Simplified mock execution - just track actions
    for agent in agents:
        rounds = random.randint(1, max_rounds)
        for _ in range(rounds):
            try:
                # Sample actions
                if len(actions_pool) > 1:
                    candidates = random.choices(actions_pool, k=2)
                    candidates.append("NONE")
                else:
                    candidates = actions_pool + ["NONE"]
                
                # Mock action selection
                selected_action = random.choice(candidates)
                # In real simulation: select_action_llm(agent, tid, candidates)
            except Exception as e:
                print(f"Error executing action for {agent.name}: {e}")


def execute_agent_actions_parallel(
    agents: List[AgentData],
    tid: int,
    actions_pool: List[str],
    max_rounds: int = 3
):
    """
    Execute agent actions in parallel using Ray.
    
    NOTE: This is a simplified demonstration showing the parallelization pattern.
    In a real simulation with proper backend setup, uncomment the Ray execution.
    
    Args:
        agents: List of agents to process
        tid: Current time slot ID
        actions_pool: Available actions
        max_rounds: Maximum actions per agent
    """
    # Prepare action parameters for each agent
    tasks = []
    for agent in agents:
        rounds = random.randint(1, max_rounds)
        for _ in range(rounds):
            # Sample actions
            if len(actions_pool) > 1:
                candidates = random.choices(actions_pool, k=2)
                candidates.append("NONE")
            else:
                candidates = actions_pool + ["NONE"]
            
            tasks.append((agent, tid, candidates))
    
    # In a real simulation with backend, use this:
    # agent_list = [task[0] for task in tasks]
    # try:
    #     results = execute_parallel_gpu('select_action_llm', agent_list, tid, actions_pool)
    #     return results
    # except Exception as e:
    #     print(f"Parallel execution failed: {e}. Falling back to sequential.")
    #     execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)
    
    # For demonstration: just show parallel pattern would be used
    print(f"      [Ray] Would execute {len(tasks)} actions in parallel")
    # Mock execution
    execute_agent_actions_sequential(agents, tid, actions_pool, max_rounds)


def execute_page_posts_parallel(
    page_agents: List[PageAgentData],
    tid: int
):
    """
    Execute page posting in parallel using Ray.
    
    NOTE: This is a simplified demonstration. In a real simulation with
    proper backend setup, uncomment the actual LLM function calls.
    
    Args:
        page_agents: List of page agents
        tid: Current time slot ID
    """
    if not page_agents:
        return
    
    # For demonstration: show the pattern without actual backend calls
    # In a real simulation with backend, uncomment this:
    # try:
    #     if RAY_AVAILABLE:
    #         results = execute_parallel_gpu('post_content', page_agents, tid)
    #     else:
    #         from y_client.functions.agent_llm_functions import post_content
    #         for page in page_agents:
    #             try:
    #                 post_content(page, tid)
    #             except Exception as e:
    #                 print(f"Error posting for page {page.name}: {e}")
    # except Exception as e:
    #     print(f"Error in page posts: {e}")
    
    # Mock demonstration
    if RAY_AVAILABLE:
        print(f"      [Ray] Would post from {len(page_agents)} pages in parallel")
    else:
        print(f"      [Sequential] Would post from {len(page_agents)} pages")


def handle_daily_follows(
    active_agents: List[AgentData],
    tid: int,
    probability: float = 0.1
):
    """
    Handle daily follow actions for a sample of agents.
    
    NOTE: This is a simplified demonstration. In a real simulation with
    proper backend setup, uncomment the actual LLM function calls.
    
    Args:
        active_agents: List of agents active today
        tid: Current time slot ID
        probability: Probability of following
    """
    # Sample agents for follow evaluation
    follow_candidates = [
        agent for agent in active_agents
        if random.random() < probability and not agent.is_page
    ]
    
    if not follow_candidates:
        return
    
    print(f"    🤝 Evaluating follows for {len(follow_candidates)} agents")
    
    # For demonstration: show the pattern without actual backend calls
    # In a real simulation with backend, uncomment this:
    # if RAY_AVAILABLE:
    #     try:
    #         execute_parallel_gpu('select_action_llm', follow_candidates, tid, ["FOLLOW", "NONE"])
    #     except:
    #         pass
    # else:
    #     from y_client.functions.agent_llm_functions import select_action_llm
    #     for agent in follow_candidates:
    #         try:
    #             select_action_llm(agent, tid, ["FOLLOW", "NONE"])
    #         except:
    #             pass


def run_simulation_pipeline(
    config: Dict,
    total_days: int = 2,
    slots_per_day: int = 24,
    num_agents: int = 10,
    num_pages: int = 2,
    use_ray: bool = True
):
    """
    Run a complete simulation pipeline with daily/hourly pattern.
    
    Args:
        config: Configuration dictionary
        total_days: Number of days to simulate
        slots_per_day: Number of time slots per day (typically 24 hours)
        num_agents: Number of user agents
        num_pages: Number of page agents
        use_ray: Whether to use Ray for parallelization
    """
    print("="*80)
    print("SIMULATION PIPELINE WITH RAY PARALLELIZATION")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Total days: {total_days}")
    print(f"  Slots per day: {slots_per_day}")
    print(f"  User agents: {num_agents}")
    print(f"  Page agents: {num_pages}")
    print(f"  Ray parallelization: {use_ray and RAY_AVAILABLE}")
    
    # Initialize Ray if requested
    if use_ray and RAY_AVAILABLE:
        print("\n Initializing Ray...")
        init_ray(num_cpus=4, num_gpus=0.5)
    elif use_ray and not RAY_AVAILABLE:
        print("\nWARNING: Ray not available, falling back to sequential execution")
    
    # Initialize simulation clock
    clock = SimulationClock(slots_per_day)
    
    # Create agents
    print(f"\nCreating {num_agents} user agents and {num_pages} page agents...")
    user_agents = []
    for i in range(num_agents):
        agent_data = create_agent_data(
            name=f"user_{i}",
            email=f"user{i}@example.com",
            config=config,
            age=20 + (i % 40),
            type="llama3",
            round_actions=3,
        )
        user_agents.append(agent_data)
    
    page_agents = []
    for i in range(num_pages):
        page_data = PageAgentData(
            name=f"news_page_{i}",
            email=f"page{i}@example.com",
            base_url=config['servers']['api'],
            feed_url=f"https://example.com/feed{i}",
            is_page=1,
        )
        page_agents.append(page_data)
    
    all_agents = user_agents + page_agents
    
    # Simplified hourly activity profile (percentage of agents active per hour)
    hourly_activity = {str(h): 0.3 + 0.4 * (1 + (h - 12)**2 / 144) for h in range(24)}
    
    # Available actions
    actions_pool = ["READ", "POST", "COMMENT", "SEARCH", "SHARE"]
    
    # Track active agents per day
    daily_active_agents: Set[str] = set()
    
    print("\nStarting simulation...")
    print("-" * 80)
    
    # DAILY LOOP
    for day in range(total_days):
        daily_active_agents.clear()
        day_start_time = datetime.now()
        
        print(f"\n📅 Day {day + 1}/{total_days}")
        print("-" * 80)
        
        # HOURLY LOOP
        for hour_idx in range(slots_per_day):
            tid, d, h = clock.get_current_slot()
            
            # Calculate expected active users for this hour
            expected_active = max(
                int(len(user_agents) * hourly_activity[str(h)]),
                1
            )
            
            print(f"  ⏰ Hour {h:02d}:00 (slot {tid}) - Expected active: {expected_active}")
            
            # Get active pages for this hour
            active_pages = get_active_pages(page_agents, h)
            
            # Pages post content
            if active_pages:
                print(f"    📰 {len(active_pages)} pages posting...")
                execute_page_posts_parallel(active_pages, tid)
            
            # Sample active user agents for this hour
            active_users = sample_agents_by_hour(
                user_agents,
                h,
                expected_active,
                hourly_activity
            )
            
            # Track daily active agents
            for agent in active_users:
                daily_active_agents.add(agent.name)
            
            if active_users:
                print(f"    👥 {len(active_users)} users active")
                
                # Execute user actions in parallel
                if use_ray and RAY_AVAILABLE:
                    execute_agent_actions_parallel(active_users, tid, actions_pool, max_rounds=3)
                else:
                    execute_agent_actions_sequential(active_users, tid, actions_pool, max_rounds=3)
            
            # Increment clock
            clock.increment_slot()
        
        # END OF DAY TASKS
        print(f"\n  📊 End of day {day + 1} summary:")
        print(f"    Total unique active users today: {len(daily_active_agents)}")
        
        # Daily follow evaluation
        probability_daily_follow = config['agents'].get('probability_of_daily_follow', 0.1)
        if probability_daily_follow > 0:
            active_agent_list = [a for a in user_agents if a.name in daily_active_agents]
            handle_daily_follows(active_agent_list, tid, probability_daily_follow)
        
        # Daily churn (simplified - just report, don't actually remove)
        churn_rate = 0.01  # 1% daily churn
        expected_churn = int(len(user_agents) * churn_rate)
        if expected_churn > 0:
            print(f"    💔 Daily churn: {expected_churn} agents")
        
        # Add new agents (simplified - just report)
        new_agents_rate = 0.02  # 2% new agents per day
        expected_new = int(len(daily_active_agents) * new_agents_rate)
        if expected_new > 0:
            print(f"    ✨ New agents: {expected_new}")
        
        day_elapsed = (datetime.now() - day_start_time).total_seconds()
        print(f"    ⏱️  Day completed in {day_elapsed:.2f} seconds")
    
    # Simulation complete
    print("\n" + "="*80)
    print("SIMULATION COMPLETE")
    print("="*80)
    print(f"Total slots processed: {clock.current_slot}")
    print(f"Total agents: {len(all_agents)}")
    
    # Cleanup
    if use_ray and RAY_AVAILABLE:
        print("\nShutting down Ray...")
        shutdown_ray()


def main():
    """Main function to run the simulation pipeline example."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run simulation pipeline with Ray parallelization'
    )
    parser.add_argument(
        '--config',
        default='config_files/config.json',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        help='Number of days to simulate'
    )
    parser.add_argument(
        '--slots',
        type=int,
        default=24,
        help='Number of time slots per day'
    )
    parser.add_argument(
        '--agents',
        type=int,
        default=10,
        help='Number of user agents'
    )
    parser.add_argument(
        '--pages',
        type=int,
        default=2,
        help='Number of page agents'
    )
    parser.add_argument(
        '--no-ray',
        action='store_true',
        help='Disable Ray parallelization'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found")
        print("Using minimal configuration...")
        config = {
            'servers': {
                'api': 'http://localhost:5000',
                'llm': 'http://localhost:8000',
            },
            'agents': {
                'attention_window': 5,
                'probability_of_daily_follow': 0.1,
                'probability_of_secondary_follow': 0.05,
            },
            'posts': {
                'emotions': ['joy', 'sadness', 'anger', 'fear'],
            },
            'simulation': {
                'actions_likelihood': {
                    'READ': 0.3,
                    'POST': 0.2,
                    'COMMENT': 0.2,
                    'SEARCH': 0.15,
                    'SHARE': 0.15,
                }
            }
        }
    
    # Run simulation
    try:
        run_simulation_pipeline(
            config=config,
            total_days=args.days,
            slots_per_day=args.slots,
            num_agents=args.agents,
            num_pages=args.pages,
            use_ray=not args.no_ray
        )
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    except Exception as e:
        print(f"\nError during simulation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
