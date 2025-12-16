"""
Base Agent Module

This module provides the core Agent class for the Y social network simulation.
Agents represent individual users who can perform various social actions like
posting, commenting, replying, liking, following, and consuming news content.

The Agent class integrates with LLM backends to generate realistic human-like
behavior, uses recommendation systems for content and follow suggestions,
and maintains personality traits based on the Big Five model.

Classes:
    - Agent: Individual user agent with social network capabilities
    - Agents: Collection/manager for multiple Agent instances
"""

import json
import random
import re
import sys
from pydoc_data.topics import topics

import numpy as np
from autogen import AssistantAgent
from pygments.lexers import archetype
from requests import get, post
from sqlalchemy.sql.expression import func
from y_client.classes.annotator import Annotator
from y_client.classes.time import SimulationSlot
from y_client.logger import log_execution_time
from y_client.news_feeds.client_modals import (
    Agent_Custom_Prompt,
    Articles,
    Images,
    Websites,
    session,
)
from y_client.news_feeds.feed_reader import NewsFeed
from y_client.recsys.ContentRecSys import ContentRecSys
from y_client.recsys.FollowRecSys import FollowRecSys
import y_client.opinion_dynamics as op_dynamics
from y_client.opinion_dynamics.utils import get_opinion_group

__all__ = ["Agent", "Agents"]


class Agent(object):
    """
    Represents an individual user agent in the Y social network simulation.
    
    The Agent class models a social network user with demographic attributes,
    personality traits, interests, and the ability to perform various social
    actions. Agents use LLM backends to generate realistic content and make
    decisions based on their personality, interests, and political leanings.
    
    Key Features:
        - Posts original content and news articles
        - Comments on and replies to posts
        - Likes and reshares content
        - Follows and unfollows other users
        - Uses content and follow recommendation systems
        - Maintains Big Five personality traits
        - Supports multiple LLM backends for content generation
        - Can process and describe images
    
    Attributes:
        name (str): Username of the agent
        email (str): Email address
        age (int): Age of the user
        gender (str): Gender
        nationality (str): Nationality
        language (str): Primary language
        interests (list): List of topics/interests
        leaning (str): Political leaning
        education_level (str): Education level
        toxicity (str): Toxicity level ("no", "low", "medium", "high")
        Big Five personality traits: oe, co, ex, ag, ne (openness, conscientiousness, 
                                    extraversion, agreeableness, neuroticism)
        type (str): LLM model type to use (e.g., "llama3", "gpt-4")
        round_actions (int): Number of actions per time slot
        user_id (int): Unique identifier assigned by the server
    """
    
    def __init__(
        self,
        name: str,
        email: str,
        pwd: str = None,
        age: int = None,
        interests: list = None,
        leaning: str = None,
        ag_type="llama3",
        load: bool = False,
        recsys: ContentRecSys = None,
        frecsys: FollowRecSys = None,
        config: dict = None,
        big_five: dict = None,
        language: str = None,
        owner: str = None,
        education_level: str = None,
        joined_on: int = None,
        round_actions: int = 3,
        gender: str = None,
        nationality: str = None,
        toxicity: str = "no",
        api_key: str = "NULL",
        is_page: int = 0,
        daily_activity_level: int = 1,
        profession: str = None,
        opinions: dict = None,
        archetype: str = None,
        *args,
        **kwargs,
    ):
        """
        Initialize an Agent with demographic, personality, and configuration attributes.
        
        This constructor can operate in two modes:
        1. Web mode (if 'web' in kwargs): Delegates to __web_init for server-based setup
        2. Standard mode: Initializes agent locally or loads from existing state
        
        Args:
            name (str): Username for the agent (no spaces)
            email (str): Email address for the agent
            pwd (str, optional): Password for authentication. Defaults to None.
            age (int, optional): Age of the user. Defaults to None.
            interests (list, optional): List of topics/interests. Defaults to None.
            leaning (str, optional): Political leaning. Defaults to None.
            ag_type (str, optional): LLM model type (e.g., "llama3", "gpt-4"). Defaults to "llama3".
            load (bool, optional): Whether to load agent from existing state. Defaults to False.
            recsys (ContentRecSys, optional): Content recommendation system instance. Defaults to None.
            frecsys (FollowRecSys, optional): Follow recommendation system instance. Defaults to None.
            config (dict, optional): Configuration dictionary with server URLs, agent parameters,
                                    and simulation settings. Defaults to None.
            big_five (dict, optional): Big Five personality traits with keys:
                                      'oe' (openness), 'co' (conscientiousness),
                                      'ex' (extraversion), 'ag' (agreeableness),
                                      'ne' (neuroticism). Defaults to None.
            language (str, optional): Primary language for content generation. Defaults to None.
            owner (str, optional): Username of the agent owner/creator. Defaults to None.
            education_level (str, optional): Education level. Defaults to None.
            joined_on (int, optional): Timestamp when agent joined the network. Defaults to None.
            round_actions (int, optional): Number of actions per time slot. Defaults to 3.
            gender (str, optional): Gender. Defaults to None.
            nationality (str, optional): Nationality. Defaults to None.
            toxicity (str, optional): Toxicity level ("no", "low", "medium", "high").
                                     Defaults to "no".
            api_key (str, optional): API key for LLM services. Defaults to "NULL" (self-hosted).
            is_page (int, optional): Flag indicating if this is a page agent (1) or user (0).
                                    Defaults to 0.
            daily_activity_level (int, optional): Activity level multiplier. Defaults to 1.
            profession (str, optional): Professional occupation. Defaults to None.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments. 'web' key triggers web initialization mode.
        
        Raises:
            Various exceptions may be raised during server communication or if required
            configuration parameters are missing.
        """

        if "web" in kwargs:
            self.__web_init(
                name=name,
                email=email,
                pwd=pwd,
                interests=interests,
                leaning=leaning,
                ag_type=ag_type,
                load=load,
                recsys=recsys,
                age=age,
                frecsys=frecsys,
                config=config,
                big_five=big_five,
                language=language,
                owner=owner,
                education_level=education_level,
                joined_on=joined_on,
                round_actions=round_actions,
                gender=gender,
                nationality=nationality,
                toxicity=toxicity,
                api_key=api_key,
                is_page=is_page,
                daily_activity_level=daily_activity_level,
                profession=profession,
                opinions=opinions,
                archetype=archetype,
                *args,
                **kwargs,
            )
        else:
            self.topics_sentiment = ""
            self.topics_opinions = ""

            self.probability_of_daily_follow = float(config["agents"][
                "probability_of_daily_follow"
            ])
            self.probability_of_secondary_follow = float(config["agents"][
                "probability_of_secondary_follow"
            ])
            self.emotions = config["posts"]["emotions"]
            self.actions_likelihood = config["simulation"]["actions_likelihood"]
            self.base_url = config["servers"]["api"].rstrip("/")
            self.llm_base = config["servers"]["llm"]
            self.content_rec_sys_name = None
            self.follow_rec_sys_name = None
            self.name = name
            self.email = email
            self.attention_window = int(config["agents"]["attention_window"])
            self.llm_v_config = {
                "url": config["servers"]["llm_v"],
                "api_key": config["servers"]["llm_v_api_key"]
                if (
                    config["servers"]["llm_v_api_key"] is not None
                    and config["servers"]["llm_v_api_key"] != ""
                )
                else "NULL",
                "model": config["agents"]["llm_v_agent"],
                "temperature": config["servers"]["llm_v_temperature"],
                "max_tokens": config["servers"]["llm_v_max_tokens"],
            }
            self.is_page = is_page
            self.opinions = opinions
            if self.opinions is not None:
                self.opinions_enabled = True
            else:
                self.opinions_enabled = False

            self.archetype = archetype

            self.opinion_dynamics = config["simulation"]['opinion_dynamics']

            print(f"Loading Preexisting simulation: {load}")

            if not load:
                self.language = language
                self.type = ag_type
                self.age = age
                self.interests = interests
                self.leaning = leaning
                self.pwd = pwd
                self.oe = big_five["oe"]
                self.co = big_five["co"]
                self.ex = big_five["ex"]
                self.ag = big_five["ag"]
                self.ne = big_five["ne"]
                self.owner = owner
                self.education_level = education_level
                self.joined_on = joined_on
                sc = SimulationSlot(config)
                sc.get_current_slot()
                self.joined_on = sc.id
                self.round_actions = round_actions
                self.gender = gender
                self.nationality = nationality
                self.toxicity = toxicity
                self.daily_activity_level = daily_activity_level
                self.profession = profession
                self.opinions = opinions

                if self.opinions is not None:
                    self.opinions_enabled = True
                else:
                    self.opinions_enabled = False
                self.opinion_dynamics = config["simulation"]['opinion_dynamics']

                self.archetype = archetype

                uid = self.__register()

                if uid is None:
                    pass
                else:
                    self.user_id = uid

            else:
                us = json.loads(self.__get_user())
                self.user_id = us["id"]
                self.type = us["user_type"]
                self.age = us["age"]

                if us["is_page"] == 0:
                    self.interests = random.randint(
                        config["agents"]["n_interests"]["min"],
                        config["agents"]["n_interests"]["max"],
                    )
                    self.interests = self.__get_interests(-1)[0]

                    if self.opinions_enabled:
                        self.opinions = self.__get_opinions()
                    else:
                        self.opinions = None
                    self.opinion_dynamics = config["simulation"]['opinion_dynamics']
                    self.archetype = archetype

                else:
                    self.interests = []

                self.leaning = us["leaning"]
                self.pwd = us["password"]
                self.oe = us["oe"]
                self.co = us["co"]
                self.ex = us["ex"]
                self.ag = us["ag"]
                self.ne = us["ne"]
                self.content_rec_sys_name = us["rec_sys"]
                self.follow_rec_sys_name = us["frec_sys"]
                self.language = us["language"]
                self.owner = us["owner"]
                self.education_level = us["education_level"]
                self.round_actions = us["round_actions"]
                self.joined_on = us["joined_on"]
                self.gender = us["gender"]
                self.toxicity = us["toxicity"]
                self.nationality = us["nationality"]
                self.is_page = us["is_page"]
                self.archetype = us['archetype'] if "archetype" in us else None

            config_list = {
                "model": f"{self.type}",
                "base_url": self.llm_base,
                "timeout": 10000,
                "api_type": "open_ai",
                "api_key": api_key
                if (api_key is not None and api_key != "")
                else "NULL",
                "price": [0, 0],
            }

            self.llm_config = {
                "config_list": [config_list],
                "seed": np.random.randint(0, 100000),
                "max_tokens": config["servers"]["llm_max_tokens"],
                # max response length, -1 no limits. Imposing limits may lead to truncated responses
                "temperature": config["servers"]["llm_temperature"],
            }

            # add and configure the content recsys
            self.content_rec_sys = recsys
            if self.content_rec_sys is not None:
                self.content_rec_sys.add_user_id(self.user_id)

            # add and configure the follow recsys
            self.follow_rec_sys = frecsys
            if self.follow_rec_sys is not None:
                self.follow_rec_sys.add_user_id(self.user_id)

            self.prompts = None

    def __web_init(
        self,
        name: str,
        email: str,
        pwd: str = None,
        age: int = None,
        interests: list = None,
        leaning: str = None,
        ag_type="llama3",
        load: bool = False,
        recsys: ContentRecSys = None,
        frecsys: FollowRecSys = None,
        config: dict = None,
        big_five: dict = None,
        language: str = None,
        owner: str = None,
        education_level: str = None,
        joined_on: int = None,
        round_actions: int = 3,
        gender: str = None,
        nationality: str = None,
        toxicity: str = "no",
        api_key: str = "NULL",
        is_page: int = 0,
        daily_activity_level: int = 1,
        profession: str = None,
        activity_profile: str = None,
        opinions: dict = None,
        archetype: str = None,
        *args,
        **kwargs,
    ):
        self.topics_sentiment = ""
        self.topics_opinions = ""

        self.probability_of_secondary_follow = float(config["agents"][
            "probability_of_secondary_follow"
        ])
        self.probability_of_daily_follow = float(config["agents"][
                                                     "probability_of_daily_follow"
                                                 ])
        self.emotions = config["posts"]["emotions"]
        self.actions_likelihood = config["simulation"]["actions_likelihood"]
        self.base_url = config["servers"]["api"].rstrip("/")
        self.llm_base = config["servers"]["llm"]
        self.content_rec_sys_name = None
        self.follow_rec_sys_name = None
        self.content_rec_sys = None
        self.follow_rec_sys = None
        self.daily_activity_level = daily_activity_level
        self.profession = profession
        self.name = name
        self.email = email
        self.attention_window = int(config["agents"]["attention_window"])
        self.activity_profile = activity_profile
        self.annotate_emotions = config["simulation"]["emotion_annotation"]
        self.opinions = opinions
        if self.opinions is not None:
            self.opinions_enabled = True
        else:
            self.opinions_enabled = False

        self.opinion_dynamics = config["simulation"]['opinion_dynamics'] if 'opinion_dynamics' in config["simulation"] else None
        self.archetype = archetype

        if "prompts" in kwargs:
            self.prompts = kwargs["prompts"]
            # save on agent custom prompt
            if self.prompts is not None:
                aprompt = Agent_Custom_Prompt(name=self.name, prompt=self.prompts)
                session.add(aprompt)
                session.commit()

        self.llm_v_config = {
            "url": config["servers"]["llm_v"],
            "api_key": config["servers"]["llm_v_api_key"]
            if (
                config["servers"]["llm_v_api_key"] is not None
                and config["servers"]["llm_v_api_key"] != ""
            )
            else "NULL",
            "temperature": config["servers"]["llm_v_temperature"],
            "max_tokens": int(config["servers"]["llm_v_max_tokens"]),
        }
        try:
            self.llm_v_config["model"] = config["servers"]["llm_v_agent"]
        except:
            self.llm_v_config["model"] = "minicpm-v"

        self.is_page = is_page

        if not load:
            self.language = language
            self.type = ag_type
            self.age = age
            self.interests = interests
            self.leaning = leaning
            self.pwd = pwd
            try:
                self.oe = big_five["oe"]
                self.co = big_five["co"]
                self.ex = big_five["ex"]
                self.ag = big_five["ag"]
                self.ne = big_five["ne"]

            except:
                self.oe = kwargs["oe"]
                self.co = kwargs["co"]
                self.ex = kwargs["ex"]
                self.ag = kwargs["ag"]
                self.ne = kwargs["ne"]

            self.toxicity = toxicity
            self.owner = owner
            self.education_level = education_level
            self.joined_on = joined_on
            sc = SimulationSlot(config)
            sc.get_current_slot()
            self.joined_on = sc.id
            self.round_actions = round_actions
            self.gender = gender
            self.nationality = nationality
            self.opinions = opinions
            self.archetype = archetype

            uid = self.__register()
            if uid is None:
                pass
            else:
                self.user_id = uid

        else:
            u = self.__get_user()
            us = json.loads(u)

            if "status" in us and us["status"] == 404:
                return

            self.user_id = us["id"]
            self.type = us["user_type"]
            self.age = us["age"]

            if us["is_page"] == 0:
                try:
                    self.interests = random.randint(
                        config["agents"]["n_interests"]["min"],
                        config["agents"]["n_interests"]["max"],
                    )
                    self.interests = self.__get_interests(-1)[0]
                except:
                    self.interests = interests
                    self.interests = self.__get_interests(-1)[0]
            else:
                self.interests = []

            self.leaning = us["leaning"]
            self.pwd = us["password"]
            self.oe = us["oe"]
            self.co = us["co"]
            self.ex = us["ex"]
            self.ag = us["ag"]
            self.ne = us["ne"]
            self.content_rec_sys_name = us["rec_sys"]
            self.follow_rec_sys_name = us["frec_sys"]
            self.language = us["language"]
            self.owner = us["owner"]
            self.education_level = us["education_level"]
            self.round_actions = us["round_actions"]
            self.joined_on = us["joined_on"]
            self.gender = us["gender"]
            self.toxicity = us["toxicity"]
            self.nationality = us["nationality"]
            self.is_page = us["is_page"]
            self.archetype = us['archetype']

            if self.opinions_enabled:
                self.opinions = self.__get_opinions()
            else:
                self.opinions = None

        config_list = {
            "model": f"{self.type}",
            "base_url": self.llm_base,
            "timeout": 10000,
            "api_type": "open_ai",
            "api_key": api_key if (api_key is not None and api_key != "") else "NULL",
            "price": [0, 0],
        }

        self.llm_config = {
            "config_list": [config_list],
            "seed": np.random.randint(0, 100000),
            "max_tokens": int(config["servers"]["llm_max_tokens"]),
            # max response length, -1 no limits. Imposing limits may lead to truncated responses
            "temperature": float(config["servers"]["llm_temperature"]),
        }

        self.set_rec_sys(recsys, frecsys)

        # add and configure the content recsys
        if self.content_rec_sys is not None:
            self.content_rec_sys.add_user_id(self.user_id)

        # add and configure the follow recsys
        if self.follow_rec_sys is not None:
            self.follow_rec_sys.add_user_id(self.user_id)

        self.prompts = None

    def __effify(self, non_f_str: str, **kwargs):
        """
        Effify the string.

        :param non_f_str: the string to effify
        :param kwargs: the keyword arguments
        :return: the effified string
        """
        kwargs["self"] = self
        return eval(f'f"""{non_f_str}"""', kwargs)

    def set_prompts(self, prompts):
        """
        Set the LLM prompts.

        :param prompts: the prompts
        """
        self.prompts = prompts

        try:
            # if the agent has custom prompts substitute the default ones
            aprompt = (
                session.query(Agent_Custom_Prompt)
                .filter_by(agent_name=self.name)
                .first()
            )
            if aprompt:
                self.prompts[
                    "agent_roleplay"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_simple"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_base"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
                self.prompts[
                    "agent_roleplay_comments_share"
                ] = f"{aprompt.prompt} - Act as requested by the Handler."
        except:
            pass

    def set_rec_sys(self, content_recsys, follow_recsys):
        """
        Set the recommendation systems.

        :param content_recsys: the content recommendation system
        :param follow_recsys: the follow recommendation system
        """
        if self.content_rec_sys is None:
            self.content_rec_sys = content_recsys
            self.content_rec_sys.add_user_id(self.user_id)
            self.content_rec_sys_name = content_recsys.name

            api_url = f"{self.base_url}/update_user"

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            params = {
                "username": self.name,
                "email": self.email,
                "recsys_type": content_recsys.name,
            }
            st = json.dumps(params)
            post(f"{api_url}", headers=headers, data=st)

        if self.follow_rec_sys is None:
            self.follow_rec_sys = follow_recsys
            self.follow_rec_sys.add_user_id(self.user_id)
            self.follow_rec_sys_name = follow_recsys.name

            api_url = f"{self.base_url}/update_user"

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            params = {
                "username": self.name,
                "email": self.email,
                "frecsys_type": follow_recsys.name,
            }
            st = json.dumps(params)
            post(f"{api_url}", headers=headers, data=st)

        return {"status": 200}

    def __extract_components(self, text, c_type="hashtags"):
        """
        Extract the components from the text.

        :param text: the text to extract the components from
        :param c_type: the component type
        :return: the extracted components
        """
        # Define the regex pattern
        if c_type == "hashtags":
            pattern = re.compile(r"#\w+")
        elif c_type == "mentions":
            pattern = re.compile(r"@\w+")
        else:
            return []
        # Find all matches in the input text
        hashtags = pattern.findall(text)
        return hashtags

    def __get_user(self):
        """
        Get the user from the service.

        :return: the user
        """
        api_url = f"{self.base_url}/get_user"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"username": self.name, "email": self.email}
        st = json.dumps(params)

        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def _check_credentials(self):
        """
        Check if the credentials are correct.

        :return: the response from the service
        """
        api_url = f"{self.base_url}/user_exists"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"name": self.name, "email": self.email}

        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        data = response.json()

        if response.status_code != 200 or data.get("status") != 200:
            return json.dumps({"status": response.status_code, "error": "User not found"})
        else:
            return json.dumps({"status": 200})

    def __register(self):
        """
        Register the agent to the service.

        :return: the response from the service
        """

        st = json.dumps(
            {
                "name": self.name,
                "email": self.email,
                "password": self.pwd,
                "leaning": self.leaning,
                "age": self.age,
                "user_type": self.type,
                "oe": self.oe,
                "co": self.co,
                "ex": self.ex,
                "ag": self.ag,
                "ne": self.ne,
                "language": self.language,
                "owner": self.owner,
                "education_level": self.education_level,
                "round_actions": self.round_actions,
                "gender": self.gender,
                "nationality": self.nationality,
                "toxicity": self.toxicity,
                "joined_on": self.joined_on,
                "is_page": self.is_page,
                "daily_activity_level": self.daily_activity_level,
                "profession": self.profession,
                "activity_profile": self.activity_profile,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/register"
        post(f"{api_url}", headers=headers, data=st)

        us = self.__get_user()
        res = json.loads(us)
        uid = int(res["id"])

        api_url = f"{self.base_url}/set_user_interests"
        data = {"user_id": uid, "interests": self.interests, "round": self.joined_on}

        post(f"{api_url}", headers=headers, data=json.dumps(data))

        if self.opinions_enabled:
            api_url = f"{self.base_url}/set_user_opinions"
            data = {"user_id": uid, "opinions": self.opinions, "round": self.joined_on}
            post(f"{api_url}", headers=headers, data=json.dumps(data))

        return uid

    def __get_opinions(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/get_user_opinions"

        data = {
            "user_id": self.user_id,
        }
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data))
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        opinions = {}
        try:
            for k, v in data.items():
                opinions[k] = v[0]
        except:
            return {}

        return opinions

    def __get_interests(self, tid):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # current round
        if tid == -1:
            # get last round id
            api_url = f"{self.base_url}/current_time"
            response = get(f"{api_url}", headers=headers)
            data = json.loads(response.__dict__["_content"].decode("utf-8"))
            tid = int(data["id"])

        api_url = f"{self.base_url}/get_user_interests"

        data = {
            "user_id": self.user_id,
            "round_id": tid,
            "n_interests": self.interests
            if isinstance(self.interests, int)
            else len(self.interests),
            "time_window": self.attention_window,
        }
        response = get(f"{api_url}", headers=headers, data=json.dumps(data))

        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        try:
            # select a random interest without replacement
            if len(data) >= 3:
                selected = np.random.choice(
                    range(len(data)), np.random.randint(1, 3), replace=False
                )
            else:
                selected = np.random.choice(range(len(data)), len(data), replace=False)

            interests = [data[i]["topic"] for i in selected]
            interests_id = [data[i]["id"] for i in selected]
        except:
            return [], []

        return interests, interests_id

    def __emotion_annotation(self, text_to_annotate: str):
        """
        Annotate the emotions in the text.

        :param text: the text to annotate
        :return: the annotated emotions
        """

        emotion_agent = AssistantAgent(
            name="EmotionAnnotator",
            llm_config=self.llm_config,
            system_message=self.prompts['handler_instructions'],
            max_consecutive_auto_reply=1,
        )

        prompt = f"Annotate the following text with the emotions it elicits:\n\n{text_to_annotate}. Answer with a JSON formatted list of emotions only."
        response = emotion_agent.generate_reply(messages=[{"role": "user", "content": prompt}])

        emotion_eval = response.lower()
        emotion_eval = self.__clean_emotion(emotion_eval)

        return emotion_eval

    @log_execution_time
    def post(self, tid):
        """
        Post a message to the service.

        :param tid: the round id
        """

        # obtain the most recent (and frequent) interests of the agent
        interests, interests_id = self.__get_interests(tid)

        self.topics_opinions = "Your opinions are: "
        self.topics_sentiment = "Your sentiment is: "

        if self.opinions_enabled:
            opinions = self.__get_opinions()
            for interest in interests:
                opinions[interest] = get_opinion_group(opinions[interest], self.opinion_dynamics['opinion_groups'])

            for s in opinions:
                self.topics_opinions += f"{s}: {opinions[s]} "
            if len(opinions) == 0:
                self.topics_opinions = ""

        # get recent sentiment on the selected interests
        api_url = f"{self.base_url}/get_sentiment"
        data = {"user_id": self.user_id, "interests": interests}
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        sentiment = json.loads(response.__dict__["_content"].decode("utf-8"))

        for s in sentiment:
            self.topics_sentiment += f"{s['topic']}: {s['sentiment']} "

        if len(sentiment) == 0:
            self.topics_sentiment = ""

        user_agent = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        prompt = self.__effify(self.prompts["handler_post"])
        post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
        post_text = self.__clean_text(post_text)

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "tweet": post_text.replace('"', ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
                "topics": interests_id,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/post"
        post(f"{api_url}", headers=headers, data=st)

        # update topic of interest with the ones used to generate the post
        api_url = f"{self.base_url}/set_user_interests"
        data = {"user_id": self.user_id, "interests": interests, "round": tid}
        post(f"{api_url}", headers=headers, data=json.dumps(data))

    def __get_thread(self, post_id: int, max_tweets=None):
        """
        Get the thread of a post.

        :param post_id: The post id to get the thread.
        :param max_tweets: The maximum number of tweets to read for context.
        """
        api_url = f"{self.base_url}/post_thread"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))

        if isinstance(res, dict) and "error" in res:
            return res

        if max_tweets is not None and len(res) > max_tweets:
            return res[-max_tweets:]

        return res

    def get_user_from_post(self, post_id: int):
        """
        Get the user from a post.

        :param post_id: The post id to get the user.
        :return: the user
        """
        api_url = f"{self.base_url}/get_user_from_post"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    def __get_article(self, post_id: int):
        """
        Get the article.

        :param post_id: The article id to get the article.
        :return: the article
        """
        api_url = f"{self.base_url}/get_article"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": int(post_id)}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        if response.status_code == 404:
            return None
        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    def __get_post(self, post_id: int):
        """
        Get the thread of a post.

        :param post_id: The post id to get the thread.
        :return: the post
        """
        api_url = f"{self.base_url}/get_post"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"post_id": post_id}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)

        res = json.loads(response.__dict__["_content"].decode("utf-8"))
        return res

    @log_execution_time
    def comment(self, post_id: int, tid, max_length_threads=None):
        """
        Generate a comment to an existing post

        :param post_id: the post id
        :param tid: the round id
        :param max_length_threads: the maximum length of the thread to read for context
        """

        conversation = self.__get_thread(post_id, max_tweets=max_length_threads)

        conv = ""

        if "error" not in conversation:
            conv = "".join(conversation)

        # obtain the most recent (and frequent) interests of the agent
        # interests, _ = self.__get_interests(tid)

        # get the post_id topics
        api_url = f"{self.base_url}/get_post_topics_name"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.topics_opinions = "Your opinions on the discussion topics are: "
        self.topics_sentiment = "Your sentiment on the discussion topics are: "

        if self.opinions_enabled:
            opinions = self.__get_opinions()
            for interest in interests:
                opinions[interest] = get_opinion_group(opinions[interest], self.opinion_dynamics['opinion_groups'])

            for s in opinions:
                self.topics_opinions += f"{s}: {opinions[s]}\n "
            if len(opinions) == 0:
                self.topics_opinions = ""

        # get the opinion on the topics (if present)

        if len(interests) > 0:
            # get recent sentiment on the selected interests
            api_url = f"{self.base_url}/get_sentiment"
            data = {"user_id": self.user_id, "interests": interests}
            response = post(
                f"{api_url}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=json.dumps(data),
            )
            sentiment = json.loads(response.__dict__["_content"].decode("utf-8"))

            for s in sentiment:
                self.topics_sentiment += f"{s['topic']}: {s['sentiment']} "
            if len(sentiment) == 0:
                self.topics_sentiment = ""

        user_agent = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        prompt = self.__effify(self.prompts["handler_comment"], conv=conv)
        post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
        post_text = self.__clean_text(post_text)

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text.replace('"', "")
                .replace(f"{self.name}", "")
                .replace(":", "")
                .replace("*", ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/comment"
        post(f"{api_url}", headers=headers, data=st)

        res = None
        if self.probability_of_secondary_follow > 0:
            res = self.__evaluate_follow(post_text, post_id, "follow", tid)

        # update topic of interest with the ones from the post
        # get the root post id
        api_url = f"{self.base_url}/get_thread_root"
        response = get(
            f"{api_url}", headers=headers, data=json.dumps({"post_id": post_id})
        )
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        self.__update_user_interests(data, tid)

        # if not followed, test unfollow
        if self.probability_of_secondary_follow > 0 and res is None:
            self.__evaluate_follow(post_text, post_id, "unfollow", tid)

        # update opinion
        if self.opinions_enabled:
            self.new_opinions(post_id, tid, post_text)

    def __update_user_interests(self, post_id, tid):
        """
        Update the user interests based on the post topics.

        :param post_id: id of the post
        :param tid: round id
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/get_post_topics"
        data = {"post_id": post_id}
        response = get(f"{api_url}", headers=headers, data=json.dumps(data))
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if len(data) > 0:
            api_url = f"{self.base_url}/set_user_interests"
            data = {"user_id": self.user_id, "interests": data, "round": tid}
            post(f"{api_url}", headers=headers, data=json.dumps(data))

    @log_execution_time
    def share(self, post_id: int, tid):
        """
        Share a post containing a news article.

        :param post_id: the post id
        :param tid: the round id
        :return: the response from the service
        """

        article = self.__get_article(post_id)
        if "status" in article:
            return

        post_text = self.__get_post(post_id)

        # obtain the most recent (and frequent) interests of the agent
        # interests, _ = self.__get_interests(tid)

        # get the post_id topics
        api_url = f"{self.base_url}/get_post_topics_name"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        # get the opinion on the topics (if present)
        self.topics_opinions = ""
        if len(interests) > 0:
            # get recent sentiment on the selected interests
            api_url = f"{self.base_url}/get_sentiment"
            data = {"user_id": self.user_id, "interests": interests}
            response = post(
                f"{api_url}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=json.dumps(data),
            )
            sentiment = json.loads(response.__dict__["_content"].decode("utf-8"))

            self.topics_opinions = (
                "Your opinion topics of the post you are responding to are: "
            )
            for s in sentiment:
                self.topics_opinions += f"{s['topic']}: {s['sentiment']} "
            if len(sentiment) == 0:
                self.topics_opinions = ""
        else:
            interests, _ = self.__get_interests(tid)

        user_agent = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interests
            ),
            max_consecutive_auto_reply=1,
        )

        prompt = self.__effify(self.prompts["handler_share"], article=article, post_text=post_text)
        post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
        post_text = (
            post_text.split(":")[-1]
            .split("-")[-1]
            .replace("@ ", "")
            .replace("  ", " ")
            .replace(". ", ".")
            .replace(" ,", ",")
            .replace("[", "")
            .replace("]", "")
            .replace("@,", "")
        )
        post_text = post_text.replace(f"@{self.name}", "")

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text.replace('"', ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/share"
        post(f"{api_url}", headers=headers, data=st)

    @log_execution_time
    def reaction(self, post_id: int, tid: int, check_follow=True):
        """
        Generate a reaction to a post/comment.

        :param post_id: the post id
        :param tid: the round id
        :param check_follow: whether to evaluate a follow cascade action
        :return: the response from the service
        """

        post_text = self.__get_post(post_id)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_reactions"], post_text=post_text
            ),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "")

        u1.reset()
        u2.reset()

        if "YES" in text.split():
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": "like",
                    "tid": tid,
                }
            )
            flag = "follow"

        elif "NO" in text.split():
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": "dislike",
                    "tid": tid,
                }
            )
            flag = "unfollow"
            # always evaluate unfollow in case of dislike
            if self.probability_of_secondary_follow > 0:
                self.__evaluate_follow(post_text, post_id, flag, tid)
        else:
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/reaction"
        post(f"{api_url}", headers=headers, data=st)

        # evaluate follow only upon explicit request
        if self.probability_of_secondary_follow > 0:
            if check_follow and flag == "follow":
                self.__evaluate_follow(post_text, post_id, flag, tid)

        # update user interests after reaction
        self.__update_user_interests(post_id, tid)

    def __evaluate_follow(self, post_text, post_id, action, tid):
        """
        Evaluate secondary follow action (tied to a given probability_of_secondary_follow)

        :param post_text: the post_text
        :param post_id: the post id
        :param action: the action, either follow or unfollow
        :param tid: the round id
        :return: the response from the service
        """

        if self.probability_of_secondary_follow > 0:
            if np.random.rand() > self.probability_of_secondary_follow:
                return None
        else:
            return None

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_follow"], post_text=post_text, action=action
            ),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "")

        u1.reset()
        u2.reset()

        if "YES" in text.split():
            if action == "follow":
                self.follow(post_id=post_id, action=action, tid=tid)
                return action
            else:
                self.follow(post_id=post_id, action=action, tid=tid)
                return action
        else:
            return None

    @log_execution_time
    def follow(
        self, tid: int, target: int = None, post_id: int = None, action="follow"
    ):
        """
        Follow a user

        :param tid: the round id
        :param action: the action, either follow or unfollow
        :param post_id: the post id
        :param post_id: the post id
        :param target: the target user id
        """

        if post_id is not None:
            target = self.get_user_from_post(post_id)

        if isinstance(target, int):

            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "target": int(target),
                    "action": action,
                    "tid": tid,
                }
            )

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            api_url = f"{self.base_url}/follow"
            post(f"{api_url}", headers=headers, data=st)

    def followers(self):
        """
        Get the followers of the user.

        :return: the response from the service
        """

        st = json.dumps({"user_id": self.user_id})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/followers"
        response = get(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def timeline(self):
        """
        Get the timeline of the user.

        :return: the response from the service
        """

        st = json.dumps({"user_id": self.user_id})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/timeline"
        response = get(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    @log_execution_time
    def cast(self, post_id: int, tid: int):
        """
        Cast a voting intention (political simulation)

        :param post_id: the post id
        :param tid: the round id
        :return: the response from the service
        """

        post_text = self.__get_post(post_id)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_cast"], post_text=post_text),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()

        u1.reset()
        u2.reset()

        data = {
            "user_id": self.user_id,
            "post_id": post_id,
            "content_type": "Post",
            "tid": tid,
            "content_id": post_id,
        }

        if "RIGHT" in text.split():
            data["vote"] = "R"
            st = json.dumps(data)

        elif "LEFT" in text.split():
            data["vote"] = "D"
            st = json.dumps(data)

        elif "NONE" in text.split():
            data["vote"] = "U"
            st = json.dumps(data)
        else:
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/cast_preference"
        post(f"{api_url}", headers=headers, data=st)

    def churn_system(self, tid):
        """
        Leave the system.

        :return:
        """
        st = json.dumps({"user_id": self.user_id, "left_on": tid})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/churn"
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    @log_execution_time
    def select_action(self, tid, actions, max_length_thread_reading=5):
        """
        Post a message to the service.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """
        np.random.shuffle(actions)
        acts = ",".join(actions)

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_base"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_simple"]),
            max_consecutive_auto_reply=0,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_action"], actions=acts),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()
        u1.reset()
        u2.reset()

        if "COMMENT" in text.split():
            candidates = json.loads(self.read())
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif "POST" in text.split():
            self.post(tid=tid)

        elif "READ" in text.split():
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.reaction(int(selected_post[0]), tid=tid)
            except:
                pass

        elif "SEARCH" in text.split():
            candidates = json.loads(self.search())
            if "status" not in candidates and len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif "FOLLOW" in text.split():
            if self.probability_of_daily_follow > 0:
                candidates = self.search_follow()
                if len(candidates) > 0:
                    tot = sum([float(v) for v in candidates.values()])
                    probs = [v / tot for v in candidates.values()]
                    selected = np.random.choice(
                        [int(c) for c in candidates],
                        p=probs,
                        size=1,
                    )[0]
                    self.follow(tid=tid, target=selected, action="follow")

        elif "SHARE" in text.split():
            candidates = json.loads(self.read(article=True))
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.share(int(selected_post[0]), tid=tid)

        elif "CAST" in text.split():
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.cast(int(selected_post[0]), tid=tid)
            except:
                pass

        elif "IMAGE" in text.split():
            image, article_id = self.select_image(tid=tid)
            if image is not None:
                self.comment_image(image, tid=tid, article_id=article_id)

        return

    @log_execution_time
    def select_action_lite(self, tid, actions, max_length_thread_reading=5):
        """
        Post a message to the service.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """
        action = np.random.choice(actions)

        if action == "COMMENT":
            candidates = json.loads(self.read())
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif action == "POST":
            self.post(tid=tid)

        elif action == "READ":
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.reaction(int(selected_post[0]), tid=tid)
            except:
                pass

        elif action == "SEARCH":
            candidates = json.loads(self.search())
            if "status" not in candidates and len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
                self.reaction(int(selected_post[0]), check_follow=False, tid=tid)

        elif action == "FOLLOW":
            if self.probability_of_daily_follow > 0:
                candidates = self.search_follow()
                if len(candidates) > 0:
                    tot = sum([float(v) for v in candidates.values()])
                    probs = [v / tot for v in candidates.values()]
                    selected = np.random.choice(
                        [int(c) for c in candidates],
                        p=probs,
                        size=1,
                    )[0]
                    self.follow(tid=tid, target=selected, action="follow")

        elif action == "SHARE":
            candidates = json.loads(self.read(article=True))
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.share(int(selected_post[0]), tid=tid)

        elif action == "CAST":
            candidates = json.loads(self.read())
            try:
                selected_post = random.sample(candidates, 1)
                self.cast(int(selected_post[0]), tid=tid)
            except:
                pass

        elif action == "IMAGE":
            image, article_id = self.select_image(tid=tid)
            if image is not None:
                self.comment_image(image, tid=tid, article_id=article_id)

        return

    @log_execution_time
    def reply(self, tid: int, max_length_thread_reading: int = 5):
        """
        Reply to a mention.

        :param tid:
        :param max_length_thread_reading:
        :return:
        """
        selected_post = json.loads(self.read_mentions())
        if "status" not in selected_post:
            if len(selected_post) > 0:
                self.comment(
                    int(selected_post['post_id']),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )
        return

    @log_execution_time
    def read(self, article=False):
        """
        Read n_posts from the service.

        :param article: Whether to read an article or not
        :return: the response from the service
        """
        return self.content_rec_sys.read(self.base_url, self.user_id, article)

    def read_mentions(self):
        """
        Read n_posts from the service.

        :return: The response from the service
        """
        return self.content_rec_sys.read_mentions(self.base_url)

    @log_execution_time
    def search(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.content_rec_sys.search(self.base_url)

    @log_execution_time
    def search_follow(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.follow_rec_sys.follow_suggestions(self.base_url)

    def select_news(self):
        """
        Select a news article from the service.

        :return: the response from the service
        """

        # Select websites with the same leaning of the agent
        candidate_websites = (
            session.query(Websites).filter(Websites.leaning == self.leaning).all()
        )

        # Select a random website
        if len(candidate_websites) == 0:
            candidate_websites = session.query(Websites).all()

        if len(candidate_websites) == 0:
            return "", ""

        # Select a random website from a list
        website = np.random.choice(candidate_websites)

        # Select a random article
        website_feed = NewsFeed(website.name, website.rss)
        website_feed.read_feed()
        article = website_feed.get_random_news()
        return article, website

    def select_image(self, tid):
        """
        Select an image

        :return: the response from the service
        """
        # randomly select an image from database
        image = session.query(Images).order_by(func.random()).first()

        # @Todo: add the case of no news sharing enabled
        if (
            "news" not in self.actions_likelihood
            or self.actions_likelihood["news"] == 0
        ):
            if image is None:
                # where to get the image from??
                return None, None
            else:
                if image.description is not None:
                    return image, None

                else:
                    # annotate the image with a description
                    an = Annotator(config=self.llm_v_config)
                    description = an.annotate(image.url)

                    if description is not None:
                        image.description = description
                        session.commit()
                    else:
                        # delete image
                        session.delete(image)
                        session.commit()
                        return None, None

                    return image, None

        # the news module is active: images will be selected among RSS shared articles
        else:
            # no image available, select a news article and extract image from it
            if image is None:
                news, website = self.select_news()

                if news == "":
                    return None, None

                # get image given article id and set the remote id
                image = session.query(Images).order_by(func.random()).first()

                if image is None:
                    return None, None
                else:
                    image.remote_article_id = None
                    session.commit()

                    # annotate the image with a description
                    an = Annotator(self.llm_v_config)
                    description = an.annotate(image.url)

                    if description is not None:
                        image.description = description
                        session.commit()
                    else:
                        # delete image
                        session.delete(image)
                        session.commit()
                        return None, None

                    return image, None

            # images available, check if they have a description
            else:
                if image.description is not None:
                    return image, None

                else:
                    # annotate the image with a description
                    an = Annotator(config=self.llm_v_config)
                    description = an.annotate(image.url)
                    if description is not None:
                        image.description = description
                        session.commit()
                    else:
                        # delete image
                        session.delete(image)
                        session.commit()
                        return None, None

                    return image, None

    @log_execution_time
    def comment_image(self, image: object, tid: int, article_id: int = None):
        """
        Comment on an image

        :param image:
        :param tid:
        :param article_id:
        :return:
        """
        # obtain the most recent (and frequent) interests of the agent
        interests, _ = self.__get_interests(tid)

        self.topics_opinions = ""

        user_agent = AssistantAgent(
            name=self.name,
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=[]
            ),
            max_consecutive_auto_reply=1,
        )

        self.topics_sentiment = ""

        prompt = self.__effify(self.prompts["handler_comment_image"], descr=image.description)
        post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
        post_text = self.__clean_text(post_text)

        emotion_eval = []
        if self.annotate_emotions:
            emotion_eval = self.__emotion_annotation(post_text)

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        hashtags = self.__extract_components(post_text, c_type="hashtags")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "text": post_text.replace('"', "")
                .replace(f"{self.name}", "")
                .replace(":", "")
                .replace("*", ""),
                "emotions": emotion_eval,
                "hashtags": hashtags,
                "tid": tid,
                "image_url": image.url,
                "image_description": image.description,
                "article_id": article_id,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/comment_image"
        post(f"{api_url}", headers=headers, data=st)

    def new_opinions(self, post_id: int, tid: int, text: str):
        """
        Get new opinions for a given post.

        :param post_id: The post id.
        :param tid: The round id.
        :param text: The text of the post.
        :return: The new opinions.
        """
        # get post topics
        api_url = f"{self.base_url}/get_post_topics"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        interests = json.loads(response.__dict__["_content"].decode("utf-8"))

        # get author of the post
        api_url = f"{self.base_url}/get_post_author"
        response = get(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps({"post_id": post_id}),
        )
        author_data = json.loads(response.__dict__["_content"].decode("utf-8"))
        author_id = author_data.get("user_id", None)

        # get opinions of the author on the topics
        api_url = f"{self.base_url}/get_user_opinions"
        data = {"user_id": author_id}
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        opinions = json.loads(response.__dict__["_content"].decode("utf-8"))

        # filter opinions to keep only those related to the post topics
        filtered_opinions = {
            v[1]: v[0]
            for t, v in opinions.items()
            if int(v[1]) in interests
        }

        # get recent opinions of the agents on the topics
        api_url = f"{self.base_url}/get_user_opinions"
        data = {"user_id": self.user_id}
        response = post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        agent_opinions = json.loads(response.__dict__["_content"].decode("utf-8"))

        # filter agent opinions to keep only those related to the post topics
        agent_filtered_opinions = {
            v[1]: v[0]
            for t, v in agent_opinions.items()
            if int(v[1]) in interests
        }

        filtered_topics = {
            v[1]: t
            for t, v in agent_opinions.items()
            if int(v[1]) in interests
        }

        method_name = self.opinion_dynamics['model_name']
        update = getattr(op_dynamics, method_name)

        for topic, opinion in filtered_opinions.items():
            if topic in agent_filtered_opinions:
                # update the opinion as the average of the two
                tp_name = filtered_topics[topic]

                agent_filtered_opinions[topic] = update(uid=self.user_id, x=agent_filtered_opinions[topic], y=opinion,
                                                        text=text, topic=tp_name,
                                                        **self.opinion_dynamics['parameters'],
                                                        group_classes=self.opinion_dynamics['opinion_groups'],
                                                        base_url=self.base_url, llm_config=self.llm_config)

        # set the new opinions
        api_url = f"{self.base_url}/set_user_opinions"

        data = {
                "user_id": self.user_id,
                "opinions": agent_filtered_opinions,
                "id_post": int(post_id),
                "id_interacted_with": int(author_id),
                "round": int(tid),
            }

        post(
            f"{api_url}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )

        return True

    def __str__(self):
        """
        Return a string representation of the Agent object.

        :return: the string representation
        """
        return f"Name: {self.name}, Age: {self.age}, Type: {self.type}"

    def __dict__(self):
        """
        Return a dictionary representation of the Agent object.

        :return: the dictionary representation
        """

        interests = self.__get_interests(-1)

        return {
            "name": self.name,
            "email": self.email,
            "password": self.pwd,
            "age": self.age,
            "type": self.type,
            "leaning": self.leaning,
            "interests": interests,
            "oe": self.oe,
            "co": self.co,
            "ex": self.ex,
            "ag": self.ag,
            "ne": self.ne,
            "rec_sys": self.content_rec_sys_name,
            "frec_sys": self.follow_rec_sys_name,
            "language": self.language,
            "owner": self.owner,
            "education_level": self.education_level,
            "round_actions": self.round_actions,
            "gender": self.gender,
            "nationality": self.nationality,
            "toxicity": self.toxicity,
            "joined_on": self.joined_on,
            "is_page": self.is_page,
            "daily_activity_level": self.daily_activity_level,
            "profession": self.profession,
            "activity_profile": self.activity_profile,
            "opinions": self.opinions,
            "archetype": self.archetype,
        }

    def __clean_emotion(self, text):
        try:
            emotion_eval = [
                e.strip()
                for e in text.replace("'", " ")
                .replace('"', " ")
                .replace("*", "")
                .replace(":", " ")
                .replace("[", " ")
                .replace("]", " ")
                .replace(",", " ")
                .split(" ")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []
        return emotion_eval

    def __clean_text(self, text):
        text = (
            text.split("##")[-1]
            .replace("-", "")
            .replace("@ ", "")
            .replace("  ", " ")
            .replace(". ", ".")
            .replace(" ,", ",")
            .replace("[", "")
            .replace("]", "")
            .replace("@,", "")
            .strip("()[]{}'")
            .lstrip()
        )
        text = text.replace(f"@{self.name}", "")
        return text


class Agents(object):
    def __init__(self):
        """
        Initialize the Agent object.
        """
        self.agents = []

    def add_agent(self, agent: Agent):
        """
        Add a profile to the Agents object.

        :param agent: The Profile object to add.
        """
        self.agents.append(agent)

    def remove_agent(self, agent: Agent):
        """
        Remove a profile from the Agents object.

        :param agent: The Profile object to remove.
        """
        self.agents.remove(agent)

    def remove_agent_by_ids(self, agent_ids: list):
        """
        Remove a profile from the Agents object.

        :param agent: The Profile object to remove.
        """
        agent_ids = {int(aid): None for aid in agent_ids}
        for agent in self.agents:
            if agent.user_id in agent_ids:
                self.agents.remove(agent)

    def get_agents(self):
        return self.agents

    def agents_iter(self):
        """
        Iterate over the agents.
        """
        for agent in self.agents:
            yield agent

    def __str__(self):
        """
        Return a string representation of the Agents object.

        :return: the string representation
        """
        return "".join([p.__str__() for p in self.agents])

    def __dict__(self):
        """
        Return a dictionary representation of the Agents object.

        :return: the dictionary representation
        """
        return {"agents": [p.__dict__() for p in self.agents]}

    def __eq__(self, other):
        """
        Return True if the Agents objects are equal.

        :param other: The other agent object to compare.
        :return: True if the Agents objects are equal.
        """
        return self.__dict__() == other.__dict__()
