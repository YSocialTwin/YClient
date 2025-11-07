"""
Web Client Module

This module provides YClientWeb, a web-based client implementation for running
Y social network simulations. Unlike the base client, this version manages
its own database connection and is designed for web application deployment.

The client handles database initialization, agent management, and simulation
execution through a web interface.

Global Variables:
    - session: SQLAlchemy database session (initialized on client creation)
    - engine: Database engine connection
    - base: SQLAlchemy declarative base
"""

import json
import os
import shutil
import sys
from pathlib import Path

import sqlalchemy as db
from requests import post
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
session = None
engine = None
base = None


class YClientWeb(object):
    """
    Web-based client for Y social network simulations.
    
    This client is designed for web application deployments and manages
    its own database connections. It provides a simpler interface compared
    to YClientBase, focusing on essential simulation features.
    
    Attributes:
        config (dict): Simulation configuration
        prompts (dict): LLM prompts for agent behaviors
        base_path (str): Base path for data files
        agents_owner (str): Owner of the simulation
        days (int): Total simulation days
        slots (int): Time slots per day
        first_run (bool): Whether this is the first simulation run
        (plus various simulation parameters from config)
    """
    
    def __init__(
        self,
        config_file,
        data_base_path,
        agents_filename=None,
        agents_output="agents.json",
        owner="admin",
        first_run=False,
        network=None,
        log_file="agent_execution.log",
        llm=True
    ):
        """
        Initialize the web-based YClient simulation environment.
        
        This constructor sets up the simulation with database connections,
        loads configuration and prompts, and prepares for agent creation
        and simulation execution.
        
        Args:
            config_file (dict): Configuration dictionary (not filename) containing
                               simulation parameters
            data_base_path (str): Path to directory containing prompts.json and other
                                 data files
            agents_filename (str, optional): Path to JSON file with pre-existing agents.
                                            Defaults to None.
            agents_output (str, optional): Path to save generated agents. 
                                          Defaults to "agents.json".
            owner (str, optional): Username of simulation owner. Defaults to "admin".
            first_run (bool, optional): Whether this is the first run (affects setup).
                                       Defaults to False.
            network (optional): Network configuration (currently unused). Defaults to None.
            log_file (str, optional): Path to the log file for agent execution time tracking.
                                     Defaults to "agent_execution.log" in the current directory.

            llm (bool, optional): Whether or not to use LLM for agent behaviors. Defaults to True.
        
        Side effects:
            - Loads prompts from data_base_path/prompts.json
            - Creates SQLite database from clean schema if it doesn't exist
            - Initializes global session, engine, and base variables for database access
            - Normalizes action likelihood probabilities to sum to 1.0
            - Configures the global logger for agent execution time tracking
        """
        from y_client.logger import set_logger
        
        # Configure the logger with the specified log file
        set_logger(log_file)

        self.llm_active = llm

        self.first_run = first_run
        self.base_path = data_base_path
        self.config = config_file

        self.prompts = json.load(open(os.path.join(data_base_path, "prompts.json"), "r"))

        self.agents_owner = owner
        self.agents_filename = agents_filename
        self.agents_output = agents_output

        self.days = int(self.config["simulation"]["days"])
        self.slots = int(self.config["simulation"]["slots"])
        self.percentage_new_agents_iteration = float(
            self.config["simulation"]["percentage_new_agents_iteration"]
        )
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
        self.fratio = float(self.config["agents"]["reading_from_follower_ratio"])
        self.max_length_thread_reading = int(
            self.config["agents"]["max_length_thread_reading"]
        )

        # posts' parameters
        self.visibility_rd = int(self.config["posts"]["visibility_rounds"])

        # emotion annotation
        self.emotions_annotation = self.config["simulation"]["emotion_annotation"]

        ##############
        BASE_DIR = os.path.dirname(os.path.abspath(__file__)).split("y_client")[0]
        if not os.path.exists(
            f"{BASE_DIR}experiments{os.sep}{self.config['simulation']['name']}.db"
        ):
            # copy the clean database to the experiments folder
            shutil.copyfile(
                f"{BASE_DIR}data_schema{os.sep}database_clean_client.db",
                f"{BASE_DIR}experiments{os.sep}{self.config['simulation']['name']}.db",
            )

        global session, engine, base
        base = declarative_base()

        # SQLite URIs always use forward slashes, use pathlib for robust conversion
        db_path = Path(BASE_DIR) / "experiments" / f"{self.config['simulation']['name']}.db"
        db_uri = db_path.as_posix()
        engine = db.create_engine(
            f"sqlite:///{db_uri}",
            connect_args={"check_same_thread": False},
        )
        base.metadata.bind = engine
        session = orm.scoped_session(orm.sessionmaker())(bind=engine)

        globals()["session"] = session
        globals()["engine"] = engine
        globals()["base"] = base
        ##############

        yclient_path = os.path.dirname(os.path.abspath(__file__)).split("y_web")[0]
        sys.path.append(f"{yclient_path}{os.sep}external{os.sep}YClient{os.sep}")

        from y_client.classes import Agent, Agents, SimulationSlot
        from y_client.news_feeds import Feeds

        # initialize simulation clock
        self.sim_clock = SimulationSlot(self.config)

        self.agents = Agents()
        self.feed = Feeds()
        self.content_recsys = None
        self.follow_recsys = None
        self.network = network

        self.pages = []

    def read_agents(self):
        """
        Read the agents from the file

        :return:
        """
        import y_client.recsys as recsys
        import y_client.recsys as frecsys
        from y_client.classes import Agent, PageAgent, FakeAgent, FakePageAgent

        # population filename
        self.agents_filename = os.path.join(
            self.base_path, f"{self.config['simulation']['population'].replace(' ', '')}.json"
        )

        print(f"Loading agents from {self.agents_filename}")

        data = json.load(open(self.agents_filename, "r"))
        for ag in data["agents"]:
            if ag["is_page"] == 0:
                self.content_recsys = getattr(recsys, ag["rec_sys"])()
                self.follow_recsys = getattr(frecsys, ag["frec_sys"])(leaning_bias=1.5)

                if self.llm_active:

                    agent = Agent(
                        name=ag["name"],
                        email=ag["email"],
                        pwd=ag["password"],
                            ag_type=ag["type"],
                            leaning=ag["leaning"],
                            interests=ag["interests"][0],
                            oe=ag["oe"],
                            co=ag["co"],
                            ex=ag["ex"],
                            ag=ag["ag"],
                            ne=ag["ne"],
                            education_level=ag["education_level"],
                            round_actions=ag["round_actions"],
                            nationality=ag["nationality"],
                            toxicity=ag["toxicity"],
                            gender=ag["gender"],
                            age=ag["age"],
                            recsys=self.content_recsys,
                            frecsys=self.follow_recsys,
                            language=ag["language"],
                            owner=ag["owner"],
                            config=self.config,
                            load=not self.first_run,
                            web=True,
                            daily_activity_level=ag["daily_activity_level"],
                            profession=ag["profession"],
                            prompt=ag["prompts"] if "prompts" in ag else None,
                            activity_profile=ag["activity_profile"]
                        )
                else:
                    agent = FakeAgent(
                        name=ag["name"],
                        email=ag["email"],
                        pwd=ag["password"],
                        ag_type=ag["type"],
                        leaning=ag["leaning"],
                        interests=ag["interests"][0],
                        oe=ag["oe"],
                        co=ag["co"],
                        ex=ag["ex"],
                        ag=ag["ag"],
                        ne=ag["ne"],
                        education_level=ag["education_level"],
                        round_actions=ag["round_actions"],
                        nationality=ag["nationality"],
                        toxicity=ag["toxicity"],
                        gender=ag["gender"],
                        age=ag["age"],
                        recsys=self.content_recsys,
                        frecsys=self.follow_recsys,
                        language=ag["language"],
                        owner=ag["owner"],
                        config=self.config,
                        load=not self.first_run,
                        web=True,
                        daily_activity_level=ag["daily_activity_level"],
                        profession=ag["profession"],
                        prompt=ag["prompts"] if "prompts" in ag else None,
                        activity_profile=ag["activity_profile"]
                    )

                agent.set_prompts(self.prompts)
                self.agents.add_agent(agent)

            else:
                big_five = {
                    "oe": "",
                    "co": "",
                    "ex": "",
                    "ag": "",
                    "ne": "",
                }

                content_recsys = getattr(recsys, "ReverseChronoPopularity")()
                follow_recsys = getattr(frecsys, "Jaccard")(leaning_bias=1.5)

                try:

                    if self.llm_active:
                        page = PageAgent(
                            name=ag["name"],
                            pwd="",
                            email=ag["email"],
                            age=0,
                            ag_type=ag["type"],
                            leaning=None,
                            interests=[],
                            config=self.config,
                            big_five=big_five,
                            language=None,
                            education_level=None,
                            owner=ag["owner"],
                            round_actions=ag["round_actions"],
                            gender=None,
                            nationality=None,
                            toxicity=None,
                            api_key="",
                            feed_url=ag["feed_url"],
                            recsys=content_recsys,
                            frecsys=follow_recsys,
                            is_page=1,
                            web=True,
                            activity_profile=ag["activity_profile"]
                        )
                    else:
                        page = FakePageAgent(
                            name=ag["name"],
                            pwd="",
                            email=ag["email"],
                            age=0,
                            ag_type=ag["type"],
                            leaning=None,
                            interests=[],
                            config=self.config,
                            big_five=big_five,
                            language=None,
                            education_level=None,
                            owner=ag["owner"],
                            round_actions=ag["round_actions"],
                            gender=None,
                            nationality=None,
                            toxicity=None,
                            api_key="",
                            feed_url=ag["feed_url"],
                            recsys=content_recsys,
                            frecsys=follow_recsys,
                            is_page=1,
                            web=True,
                            activity_profile=ag["activity_profile"]
                        )

                    page.set_prompts(self.prompts)
                    self.agents.add_agent(page)
                    self.pages.append(
                        {
                            "name": ag["name"],
                            "feed": ag["feed_url"],
                            "leaning": ag["leaning"],
                            "category": ag["type"],
                        }
                    )

                except:
                    print(f"Error loading page agent: {ag['name']}")
                    continue

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

    def save_agents(self, agent_file):
        """
        Save the agents to a file
        """
        res = self.agents.__dict__()

        json.dump(res, open(agent_file, "w"), indent=4)

    def load_existing_agents(self, a_file):
        """
        Load existing agents from a file
        :param a_file: the JSON file containing the agents
        """
        agents = json.load(open(a_file, "r"))
        from y_client.classes import Agent, PageAgent, FakeAgent, FakePageAgent

        for a in agents["agents"]:
            try:
                if a["is_page"] == 0:
                    if self.llm_active:
                        ag = Agent(
                            name=a["name"],
                            email=a["email"],
                            load=True,
                            config=self.config,
                            web=True,
                        )
                    else:
                        ag = FakeAgent(
                            name=a["name"],
                            email=a["email"],
                            load=True,
                            config=self.config,
                            web=True,
                        )

                    ag.set_prompts(self.prompts)
                    ag.set_rec_sys(self.content_recsys, self.follow_recsys)
                    self.agents.add_agent(ag)
                else:
                    if self.llm_active:
                        ag = PageAgent(
                            a["name"],
                            email=a["email"],
                            load=True,
                            config=self.config,
                            web=True,
                        )
                    else:
                        ag = FakePageAgent(
                            a["name"],
                            email=a["email"],
                            load=True,
                            config=self.config,
                            web=True,
                        )
                    ag.set_prompts(self.prompts)
                    ag.set_rec_sys(self.content_recsys, self.follow_recsys)
                    self.agents.add_agent(ag)
                    self.pages.append(ag)
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

    def add_agent(self, agent=None):
        """
        Add an agent to the simulation

        :param agent: the agent to add
        """
        from y_client.utils import generate_user

        if agent is None:
            # try:

            agent = generate_user(self.config, owner=self.agents_owner)

            if agent is None:
                return
            agent.set_prompts(self.prompts)
            agent.set_rec_sys(self.content_recsys, self.follow_recsys)
        # except Exception:
        #     pass
        if agent is not None:
            self.agents.add_agent(agent)

    def add_feeds(self):
        for page in self.pages:
            self.feed.add_feed(
                name=page["name"],
                url_feed=page["feed"],
                category=page["category"],
                leaning=page["leaning"],
            )

    def add_network(self):
        users_id_map = {}

        if self.first_run and self.network is not None:  # self.run
            with open(os.path.join(self.base_path, self.network), "r") as f:
                headers = {"Content-Type": "application/x-www-form-urlencoded"}

                for l in f:
                    l = l.strip().split(",")

                    # from username to id on the server
                    if l[0] not in users_id_map:
                        api_url = f"{self.config['servers']['api']}get_user_id"
                        data = {
                            "username": l[0],
                        }
                        uid = post(f"{api_url}", headers=headers, data=json.dumps(data))

                        users_id_map[l[0]] = json.loads(
                            uid.__dict__["_content"].decode("utf-8")
                        )["id"]

                    if l[1] not in users_id_map:
                        api_url = f"{self.config['servers']['api']}get_user_id"
                        data = {
                            "username": l[1],
                        }
                        uid = post(f"{api_url}", headers=headers, data=json.dumps(data))
                        users_id_map[l[1]] = json.loads(
                            uid.__dict__["_content"].decode("utf-8")
                        )["id"]

                    api_url = f"{self.config['servers']['api']}follow"

                    data = {
                        "user_id": users_id_map[l[0]],
                        "target": users_id_map[l[1]],
                        "action": "follow",
                        "tid": 0,  # first round
                    }

                    post(f"{api_url}", headers=headers, data=json.dumps(data))
