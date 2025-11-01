"""
Client Base Module

This module provides the base client class for running Y social network simulations.
YClientBase handles the core simulation logic including agent management, time progression,
action scheduling, and configuration management.

Classes:
    - YClientBase: Base client for managing and running social network simulations
"""

import json
import os
import random
import sys

import networkx as nx
import tqdm
from requests import post

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from y_client import Agent, Agents, SimulationSlot
from y_client.logger import set_logger
from y_client.news_feeds import Articles, Feeds, Images, Websites, session
from y_client.recsys import *
from y_client.utils import generate_user


class YClientBase(object):
    """
    Base client class for managing and running Y social network simulations.
    
    This class orchestrates the simulation by managing:
    - Agent creation, loading, and lifecycle
    - Time progression through days and hourly slots
    - Action scheduling and execution
    - Recommendation systems for content and follows
    - News feed management
    - Social network graph structure
    
    Attributes:
        prompts (dict): LLM prompts for agent behaviors
        config (dict): Simulation configuration parameters
        agents (Agents): Collection of all active agents
        feed (Feeds): News feed manager
        sim_clock (SimulationSlot): Simulation time tracker
        content_recsys (ContentRecSys): Content recommendation system
        follow_recsys (FollowRecSys): Follow recommendation system
        days (int): Total days to simulate
        slots (int): Time slots (hours) per day
        n_agents (int): Initial number of agents
        g (nx.Graph): Social network graph structure
    """
    
    def __init__(
        self,
        config_filename,
        prompts_filename=None,
        agents_filename=None,
        graph_file=None,
        agents_output="agents.json",
        owner="admin",
        log_file="agent_execution.log",
    ):
        """
        Initialize the YClient simulation environment.
        
        This constructor sets up the simulation by loading configuration files,
        initializing the simulation clock, preparing agent management structures,
        and optionally loading a social network graph.
        
        Args:
            config_filename (str): Path to JSON configuration file containing simulation
                                  parameters (days, slots, agents, actions, etc.)
            prompts_filename (str, optional): Path to JSON file with LLM prompts for agent
                                             behaviors. Required for agent creation. Defaults to None.
            agents_filename (str, optional): Path to JSON file with pre-existing agents to load.
                                            If None, agents will be generated. Defaults to None.
            graph_file (str, optional): Path to CSV edge list file defining the social network
                                       structure. If None, no initial network is created.
                                       Defaults to None.
            agents_output (str, optional): Path to save generated agents to JSON file.
                                          Defaults to "agents.json".
            owner (str, optional): Username of the simulation owner/administrator.
                                  Defaults to "admin".
            log_file (str, optional): Path to the log file for agent execution time tracking.
                                     Defaults to "agent_execution.log" in the current directory.
        
        Raises:
            Exception: If prompts_filename is None (prompts are required)
        
        Side effects:
            - Loads configuration and prompts from files
            - Initializes simulation clock and syncs with server
            - Creates agent and feed management structures
            - Loads social network graph if provided
            - Normalizes action likelihood probabilities to sum to 1.0
            - Configures the global logger for agent execution time tracking
        """
        if prompts_filename is None:
            raise Exception("Prompts file not found")

        # Configure the logger with the specified log file
        set_logger(log_file)

        self.prompts = json.load(open(prompts_filename, "r"))
        self.config = json.load(open(config_filename, "r"))
        self.agents_owner = owner
        self.agents_filename = agents_filename
        self.agents_output = agents_output

        self.days = self.config["simulation"]["days"]
        self.slots = self.config["simulation"]["slots"]
        self.n_agents = self.config["simulation"]["starting_agents"]
        self.percentage_new_agents_iteration = self.config["simulation"][
            "percentage_new_agents_iteration"
        ]
        self.hourly_activity = self.config["simulation"]["hourly_activity"]
        self.percentage_removed_agents_iteration = float(
            self.config["simulation"]["percentage_removed_agents_iteration"]
        )
        self.actions_likelihood = {
            a.upper(): float(v)
            for a, v in self.config["simulation"]["actions_likelihood"].items()
        }
        tot = sum(self.actions_likelihood.values())
        self.actions_likelihood = {
            k: v / tot for k, v in self.actions_likelihood.items()
        }

        # users' parameters
        self.fratio = self.config["agents"]["reading_from_follower_ratio"]
        self.max_length_thread_reading = self.config["agents"][
            "max_length_thread_reading"
        ]

        # posts' parameters
        self.visibility_rd = self.config["posts"]["visibility_rounds"]

        # initialize simulation clock
        self.sim_clock = SimulationSlot(self.config)

        self.agents = Agents()
        self.feed = Feeds()
        self.content_recsys = None
        self.follow_recsys = None

        if graph_file is not None:
            self.g = nx.read_edgelist(graph_file, delimiter=",", nodetype=int)
            # relabel nodes to start from 0 just in case
            self.g = nx.convert_node_labels_to_integers(self.g, first_label=0)
        else:
            self.g = None

        self.pages = []

    @staticmethod
    def reset_news_db():
        """
        Clear all entries from the news database.
        
        This static method deletes all articles, websites, and images from
        the local news database. Useful for starting fresh or cleaning up
        between simulation runs.
        
        Side effects:
            Deletes all records from Articles, Websites, and Images tables
            and commits the transaction.
        """
        session.query(Articles).delete()
        session.query(Websites).delete()
        session.query(Images).delete()
        session.commit()

    def reset_experiment(self):
        """
        Reset the simulation experiment on the server.
        
        This method calls the server's reset endpoint to clear all simulation
        data including posts, comments, likes, follows, and agent state.
        Use this to start a new simulation run with a clean slate.
        
        Side effects:
            Sends POST request to server's /reset endpoint which deletes
            all simulation data on the server side.
        """
        api_url = f"{self.config['servers']['api']}reset"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        post(f"{api_url}", headers=headers)

    def load_rrs_endpoints(self, filename):
        """
        Load RSS feed endpoints from a JSON configuration file.
        
        This method reads a JSON file containing RSS feed information and
        registers each feed in the system. Feeds are used to populate news
        content for page agents to share.
        
        Args:
            filename (str): Path to JSON file with feed configurations.
                           Each entry should contain: name, feed_url, category, leaning
        
        Side effects:
            Adds feeds to the feed manager using self.feed.add_feed()
        """

        data = json.load(open(filename))
        for f in tqdm.tqdm(data):
            self.feed.add_feed(
                name=f["name"],
                url_feed=f["feed_url"],
                category=f["category"],
                leaning=f["leaning"],
            )

    def set_interests(self):
        """
        Configure available interests on the server.
        
        This method sends the list of possible interests from the configuration
        to the server. These interests are used by agents for content filtering
        and personalization.
        
        Side effects:
            Sends POST request to server's /set_interests endpoint with the
            interests list from config["agents"]["interests"]
        """
        api_url = f"{self.config['servers']['api']}set_interests"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = self.config["agents"]["interests"]

        post(f"{api_url}", headers=headers, data=json.dumps(data))

    def set_recsys(self, c_recsys, f_recsys):
        """
        Configure recommendation systems for agents.
        
        This method assigns content and follow recommendation system instances
        to the client. These systems are used by agents to discover relevant
        content and suggest users to follow.
        
        Args:
            c_recsys (ContentRecSys): Content recommendation system instance
            f_recsys (FollowRecSys): Follow recommendation system instance
        """
        self.content_recsys = c_recsys
        self.follow_recsys = f_recsys

    def add_agent(self, agent=None):
        """
        Add an agent to the simulation.
        
        This method either adds a provided agent or generates a new random agent
        using the configured parameters. The agent is assigned recommendation
        systems and added to the agents collection.
        
        Args:
            agent (Agent, optional): Pre-configured agent to add. If None, generates
                                    a new random agent. Defaults to None.
        
        Side effects:
            - Generates agent if None provided
            - Assigns recommendation systems to the agent
            - Adds agent to self.agents collection
        """
        if agent is None:
            try:
                agent = generate_user(self.config, owner=self.agents_owner)

                if agent is None:
                    return
                agent.set_prompts(self.prompts)
                agent.set_rec_sys(self.content_recsys, self.follow_recsys)
            except Exception:
                pass
        if agent is not None:
            self.agents.add_agent(agent)

    def create_initial_population(self):
        """
        Create the initial population of agents
        """
        # setting global interests
        self.set_interests()

        if self.agents_filename is None:
            for _ in range(self.n_agents):
                self.add_agent()

            # if specified, create the initial friendship graph
            if self.g is not None:
                tid, _, _ = self.sim_clock.get_current_slot()

                id_to_agent = {i: agent for i, agent in enumerate(self.agents.agents)}

                for u, v in self.g.edges():
                    try:
                        fr_a = id_to_agent[u]
                        to_a = id_to_agent[v]
                        fr_a.follow(tid=tid, target=to_a.user_id)
                    except Exception:
                        pass

        else:
            ags = json.load(open(self.agents_filename))
            for data in ags:
                agent = Agent(
                    name=data["name"],
                    email=data["email"],
                    config=self.config,
                    load=True,
                )

                agent.set_prompts(self.prompts)
                self.add_agent(agent)

    def save_agents(self):
        """
        Save the agents to a file
        """
        res = self.agents.__dict__()
        json.dump(res, open(self.agents_output, "w"), indent=4)

    def load_existing_agents(self, a_file):
        """
        Load existing agents from a file
        :param a_file: the JSON file containing the agents
        """
        agents = json.load(open(a_file, "r"))

        for a in agents["agents"]:
            try:
                ag = Agent(
                    name=a["name"], email=a["email"], load=True, config=self.config
                )
                ag.set_prompts(self.prompts)
                ag.set_rec_sys(self.content_recsys, self.follow_recsys)
                self.agents.add_agent(ag)
            except Exception:
                print(f"Error loading agent: {a['name']}")

    def churn(self, tid):
        """
        Evaluate churn

        :param tid:
        :return:
        """

        if self.percentage_removed_agents_iteration > 0:
            n_users = max(
                1,
                int(len(self.agents.agents) * self.percentage_removed_agents_iteration),
            )
            st = json.dumps({"n_users": n_users, "left_on": tid})

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            api_url = f"{self.config['servers']['api']}/churn"
            response = post(f"{api_url}", headers=headers, data=st)

            data = json.loads(response.__dict__["_content"].decode("utf-8"))["removed"]

            self.agents.remove_agent_by_ids(data)

    def run_simulation(self):
        """
        Run the simulation
        """

        for day in tqdm.tqdm(range(self.days)):
            print(f"\n\nDay {day} of simulation\n")
            daily_active = {}
            tid, _, _ = self.sim_clock.get_current_slot()

            for _ in tqdm.tqdm(range(self.slots)):
                tid, _, h = self.sim_clock.get_current_slot()

                # get expected active users for this time slot (at least 1)
                expected_active_users = max(
                    int(len(self.agents.agents) * self.hourly_activity[str(h)]), 1
                )

                sagents = random.sample(self.agents.agents, expected_active_users)

                # available actions
                acts = [a for a, v in self.actions_likelihood.items() if v > 0]

                # shuffle agents
                random.shuffle(sagents)
                for g in tqdm.tqdm(sagents):
                    daily_active[g.name] = None

                    for _ in range(g.round_actions):
                        # sample two elements from a list with replacement
                        candidates = random.choices(
                            acts,
                            k=2,
                            weights=[self.actions_likelihood[a] for a in acts],
                        )
                        candidates.append("NONE")

                        # reply to received mentions
                        if g not in self.pages:
                            g.reply(tid=tid)

                        # select action to be performed
                        g.select_action(
                            tid=tid,
                            actions=candidates,
                            max_length_thread_reading=self.max_length_thread_reading,
                        )
                # increment slot
                self.sim_clock.increment_slot()

            # evaluate following (once per day, only for a random sample of daily active agents)
            da = [
                agent
                for agent in self.agents.agents
                if agent.name in daily_active
                and agent not in self.pages
                and random.random()
                < float(self.config["agents"]["probability_of_daily_follow"])
            ]

            print("\n\nEvaluating new friendship ties")
            for agent in tqdm.tqdm(da):
                if agent not in self.pages:
                    agent.select_action(tid=tid, actions=["FOLLOW", "NONE"])

            total_users = len(self.agents.agents)

            # daily churn
            self.churn(tid)

            # daily new agents
            if self.percentage_new_agents_iteration > 0:
                for _ in range(
                    max(
                        1,
                        int(len(daily_active) * self.percentage_new_agents_iteration),
                    )
                ):
                    self.add_agent()

            # saving "living" agents at the end of the day
            if (
                self.percentage_removed_agents_iteration != 0
                or self.percentage_removed_agents_iteration != 0
            ):
                self.save_agents()

            print(
                f"\n\nTotal Users: {total_users}\nActive users: {len(daily_active)}\nUsers at the end of the day: {len(self.agents.agents)}\n"
            )
