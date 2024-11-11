from y_client.clients.client_base import YClientBase
from y_client.utils import generate_page
import tqdm


class YClientWithPages(YClientBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def add_page_agent(self, agent=None, name=None, feed_url=None):
        """
        Add an agent to the simulation

        :param agent: the agent to add
        """
        if agent is None:
            agent = generate_page(self.config, name=name, feed_url=feed_url, owner=self.agents_owner)
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
