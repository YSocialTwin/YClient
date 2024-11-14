from y_client.clients.client_base import YClientBase
from y_client.utils import generate_page
import tqdm
import json
from y_client import Agent, PageAgent


class YClientWithPages(YClientBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []
        self.page = None

    def load_existing_agents(self, a_file):
        """
        Load existing agents from a file
        :param a_file: the JSON file containing the agents
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
            except Exception:
                print(f"Error loading agent: {a['name']}")

    def add_page_agent(self, agent=None, name=None, feed_url=None):
        """
        Add an agent to the simulation

        :param agent: the agent to add
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
        Run the simulation
        """
        # add the page agents
        print("\nAdding page agents\n")
        for feed in tqdm.tqdm(self.feed.get_feeds()):
            self.add_page_agent(name=feed.name, feed_url=feed.feed_url)

        super().run_simulation()
