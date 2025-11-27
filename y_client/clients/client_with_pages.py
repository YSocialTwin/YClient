"""
Client With Pages Module

This module extends YClientBase to support page agents (news sources) in
addition to regular user agents. Pages automatically publish news content
from RSS feeds during the simulation.
"""

import json

import tqdm
from y_client import Agent, PageAgent
from y_client.clients.client_base import YClientBase
from y_client.logger import log_error
from y_client.utils import generate_page


class YClientWithPages(YClientBase):
    """
    Extended client that supports both user and page agents.
    
    This class adds functionality for creating and managing page agents
    (news sources) alongside regular user agents. Pages automatically
    post news articles from their RSS feeds during simulation.
    
    Attributes:
        pages (list): List of PageAgent instances
        page (PageAgent): Current page being processed (if any)
        (inherits all other attributes from YClientBase)
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize YClientWithPages instance.
        
        Args:
            *args: Variable length argument list passed to YClientBase
            **kwargs: Arbitrary keyword arguments passed to YClientBase
        """
        super().__init__(*args, **kwargs)
        self.pages = []
        self.page = None

    def load_existing_agents(self, a_file):
        """
        Load both user and page agents from a JSON file.
        
        This method loads previously saved agents and pages, distinguishing
        between them using the is_page flag, and initializes them with
        prompts and recommendation systems.
        
        Args:
            a_file (str): Path to JSON file containing agent definitions.
                         File should have format: {"agents": [{...}, ...]}
        
        Side effects:
            - Adds loaded agents to self.agents collection
            - Adds page agents to self.pages list
            - Prints error messages for agents that fail to load
        """
        agents = json.load(open(a_file, "r"))

        for a in agents["agents"]:
            try:
                if a["is_page"] == 0:
                    ag = Agent(
                        name=a["name"], email=a["email"], load=True, config=self.config
                    )
                    ag.set_prompts(self.prompts)
                    ag.set_rec_sys(self.content_recsys, self.follow_recsys)
                    self.agents.add_agent(ag)
                else:
                    ag = PageAgent(
                        a["name"], email=a["email"], load=True, config=self.config
                    )
                    ag.set_prompts(self.prompts)
                    ag.set_rec_sys(self.content_recsys, self.follow_recsys)
                    self.agents.add_agent(ag)
                    self.pages.append(ag)
            except Exception as e:
                log_error(f"Error loading agent: {a['name']}: {e}", context="load_existing_agents")

    def add_page_agent(self, agent=None, name=None, feed_url=None):
        """
        Add a page agent (news source) to the simulation.
        
        This method either adds a provided page agent or generates a new one
        with the specified name and RSS feed URL.
        
        Args:
            agent (PageAgent, optional): Pre-configured page agent. If None,
                                        generates new agent. Defaults to None.
            name (str, optional): Name for the page/news source. Defaults to None.
            feed_url (str, optional): RSS feed URL for the page. Defaults to None.
        
        Side effects:
            - Generates page agent if None provided
            - Sets prompts for the agent
            - Adds agent to self.agents and self.pages
        """
        if agent is None:
            agent = generate_page(
                self.config, name=name, feed_url=feed_url, owner=self.agents_owner
            )
            if agent is None:
                return
            agent.set_prompts(self.prompts)

        if agent is not None:
            self.agents.add_agent(agent)

        self.pages.append(agent)

    def run_simulation(self):
        """
        Run the simulation with both user and page agents.
        
        This method first creates page agents for all registered feeds,
        then delegates to the parent class's run_simulation() to execute
        the full simulation with users and pages.
        
        Side effects:
            Creates one PageAgent for each feed in self.feed.get_feeds()
            and then runs the parent simulation loop
        """
        # add the page agents
        print("\nAdding page agents\n")
        for feed in tqdm.tqdm(self.feed.get_feeds()):
            self.add_page_agent(name=feed.name, feed_url=feed.feed_url)

        super().run_simulation()
