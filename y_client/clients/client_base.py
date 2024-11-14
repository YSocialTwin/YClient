import random
import tqdm
import sys
import os
import networkx as nx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from y_client import Agent, Agents, SimulationSlot
from y_client.recsys import *
from y_client.utils import generate_user
from y_client.news_feeds import Feeds, session, Websites, Articles, Images


class YClientBase(object):
    def __init__(
        self,
        config_filename,
        prompts_filename=None,
        agents_filename=None,
        graph_file=None,
        agents_output="agents.json",
        owner="admin",
    ):
        """
        Initialize the YClient object

        :param config_filename: the configuration file for the simulation in JSON format
        :param prompts_filename: the LLM prompts file for the simulation in JSON format
        :param agents_filename: the file containing the agents in JSON format
        :param graph_file: the file containing the graph of the agents in CSV format, where the number of nodes is equal to the number of agents
        :param agents_output: the file to save the generated agents in JSON format
        :param owner: the owner of the simulation
        """
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
        Reset the news database
        """
        session.query(Articles).delete()
        session.query(Websites).delete()
        session.query(Images).delete()
        session.commit()

    def reset_experiment(self):
        """
        Reset the experiment
        Delete all agents and reset the server database
        """
        api_url = f"{self.config['servers']['api']}reset"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        post(f"{api_url}", headers=headers)

    def load_rrs_endpoints(self, filename):
        """
        Load rss feeds from a file

        :param filename: the file containing the rss feeds
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
        Set the interests of the agents
        """
        api_url = f"{self.config['servers']['api']}set_interests"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = self.config["agents"]["interests"]

        post(f"{api_url}", headers=headers, data=json.dumps(data))

    def set_recsys(self, c_recsys, f_recsys):
        """
        Set the recommendation systems

        :param c_recsys: the content recommendation system
        :param f_recsys: the follower recommendation system
        """
        self.content_recsys = c_recsys
        self.follow_recsys = f_recsys

    def add_agent(self, agent=None):
        """
        Add an agent to the simulation

        :param agent: the agent to add
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
                        int(
                            len(self.agents.agents)
                            * self.percentage_new_agents_iteration
                        ),
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
