import random
import tqdm
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from y_client import Agent, Agents, SimulationSlot
from y_client.recsys import *
from y_client.utils import generate_user
from y_client.news_feeds import Feeds, session, Websites, Articles


class YClient(object):
    def __init__(
        self,
        config_filename,
        prompts_filename=None,
        agents_filename=None,
        agents_output="agents.json",
        owner="admin",
    ):
        if prompts_filename is None:
            raise Exception("Prompts file not found")

        self.prompts = json.load(open(prompts_filename, "r"))
        self.config = json.load(open(config_filename, "r"))
        self.agents_owner = owner
        self.agents_filename = agents_filename
        self.agents_output = agents_output

        self.days = self.config["simulation"]["days"]
        self.slots = self.config["simulation"]["slots"]
        self.n_agents = self.config["simulation"]["starting_agents"]
        self.new_agents_iteration = self.config["simulation"]["new_agents_iteration"]
        self.hourly_activity = self.config["simulation"]["hourly_activity"]

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

    @staticmethod
    def reset_news_db():
        session.query(Articles).delete()
        session.query(Websites).delete()
        session.commit()

    def reset_experiment(self):
        api_url = f"{self.config['servers']['api']}reset"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        post(f"{api_url}", headers=headers)

    def load_rrs_endpoints(self, filename):

        data = json.load(open(filename))
        for f in tqdm.tqdm(data):
            self.feed.add_feed(
                name=f["name"],
                url_feed=f["feed_url"],
                category=f["category"],
                leaning=f["leaning"],
            )

    def set_recsys(self, c_recsys, f_recsys):
        self.content_recsys = c_recsys
        self.follow_recsys = f_recsys

    def add_agent(self, agent=None):
        if agent is None:
            try:
                agent = generate_user(self.config, owner=agents_owner)
                agent.set_prompts(self.prompts)
                agent.set_rec_sys(self.content_recsys, self.follow_recsys)
            except Exception:
                print("User not found")
        if agent is not None:
            self.agents.add_agent(agent)

    def create_initial_population(self):
        if self.agents_filename is None:
            for _ in range(self.n_agents):
                self.add_agent()
        else:
            ags = json.load(open(self.agents_filename))
            for data in ags:
                agent = Agent(
                    name=data["name"],
                    email=data["email"],
                    config=self.config,
                    load=True,
                )

                print(self.prompts)
                exit()
                agent.set_prompts(self.prompts)
                self.add_agent(agent)

    def save_agents(self):
        res = self.agents.__dict__()
        json.dump(res, open(self.agents_output, "w"), indent=4)

    def load_existing_agents(self, a_file):
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

    def run_simulation(self):

        for day in tqdm.tqdm(range(self.days)):
            print(f"Day {day} of simulation")
            daily_active = {}
            tid, _, _ = self.sim_clock.get_current_slot()

            for _ in range(self.new_agents_iteration):
                self.add_agent()

            if self.new_agents_iteration != 0:
                self.save_agents()

            for _ in tqdm.tqdm(range(self.slots)):
                tid, _, h = self.sim_clock.get_current_slot()

                # get expected active users for this time slot
                expected_active_users = int(
                    len(self.agents.agents) * self.hourly_activity[str(h)]
                )
                sagents = random.sample(self.agents.agents, expected_active_users)

                # shuffle agents
                random.shuffle(sagents)
                for g in tqdm.tqdm(sagents):
                    daily_active[g.name] = None
                    # select action to be performed
                    g.select_action(tid=tid, actions=["NEWS", "POST", "NONE"])
                    g.select_action(
                        tid=tid,
                        actions=["COMMENT", "REPLY", "NONE"],
                        max_length_thread_reading=self.max_length_thread_reading,
                    )
                    g.select_action(
                        tid=tid,
                        actions=["SHARE", "READ", "NONE"],
                        max_length_thread_reading=self.max_length_thread_reading,
                    )

                # increment slot
                self.sim_clock.increment_slot()

            # evaluate following and hashtag search (once per day, only for daily active agents)
            da = [agent for agent in self.agents.agents if agent.name in daily_active]
            print("Evaluating new friendship ties")
            for agent in tqdm.tqdm(da):
                agent.select_action(tid=tid, actions=["FOLLOW", "SEARCH", "NONE"])


if __name__ == "__main__":

    from argparse import ArgumentParser
    import y_client.recsys

    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--config_file",
        default="../config_files/config.json",
        help="JSON file describing the simulation configuration",
    )
    parser.add_argument(
        "-f",
        "--feeds",
        default="../config_files/rss_feeds.json",
        help="JSON file containing rss feed categorized",
    )
    parser.add_argument(
        "-p",
        "--prompts",
        default="../config_files/prompts.json",
        help="JSON file containing LLM prompts",
    )
    parser.add_argument(
        "-a", "--agents", default=None, help="JSON file with pre-existing agents"
    )
    parser.add_argument(
        "-o", "--owner", default="admin", help="Simulation owner username"
    )
    parser.add_argument(
        "-r",
        "--reset",
        default=False,
        help="Boolean. Whether to reset the experiment status. Default False",
    )
    parser.add_argument(
        "-n",
        "--news",
        default=False,
        help="Boolean. Whether to reload the rss feeds. Default False",
    )
    parser.add_argument(
        "-x",
        "--crecsys",
        default="ReverseChronoFollowersPopularity",
        help="Name of the content recsys to be used. Options: ...",
    )
    parser.add_argument(
        "-y",
        "--frecsys",
        default="PreferentialAttachment",
        help="Name of the follower recsys to be used. Options: ...",
    )
    parser.add_argument(
        "-w",
        "--write_output",
        default="../config_files/agents.json",
        help="Name of the output file storing the generated agents",
    )

    args = parser.parse_args()

    agents_owner = args.owner
    config_file = args.config_file
    agents_file = args.agents
    rss_feeds = args.feeds
    output = args.write_output
    prompts_file = args.prompts

    content_recsys = getattr(y_client.recsys, args.crecsys)()
    follow_recsys = getattr(y_client.recsys, args.frecsys)(leaning_bias=1.5)

    experiment = YClient(
        config_file,
        prompts_file,
        agents_filename=agents_file,
        owner=agents_owner,
        agents_output=output,
    )

    if args.reset:
        experiment.reset_experiment()
    if args.news:
        experiment.reset_news_db()
        experiment.load_rrs_endpoints(rss_feeds)

    experiment.set_recsys(content_recsys, follow_recsys)

    if args.agents is None:
        experiment.create_initial_population()
    else:
        experiment.load_existing_agents(args.agents)

    experiment.save_agents()
    experiment.run_simulation()
