from y_client.recsys.ContentRecSys import ContentRecSys
from y_client.recsys.FollowRecSys import FollowRecSys
from y_client.news_feeds.client_modals import Websites, session
from y_client.news_feeds.feed_reader import NewsFeed
import random
from requests import get, post
import json
from autogen import AssistantAgent
import numpy as np
import re


__all__ = ["Agent", "Agents", "SimulationSlot"]


class SimulationSlot(object):
    def __init__(self, config):
        """
        Initialize the SimulationSlot object.

        :param config: the configuration dictionary
        """
        self.base_url = config["servers"]["api"]

        api_url = f"{self.base_url}current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]

    def get_current_slot(self):
        """
        Get the current slot.

        :return: the current slot, day and id
        """
        return self.id, self.day, self.slot

    def increment_slot(self):
        """
        Update the current slot.
        """
        api_url = f"{self.base_url}update_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if self.slot < 23:
            slot = self.slot + 1
            day = self.day
        else:
            slot = 0
            day = self.day + 1

        params = {"day": day, "round": slot}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = int(data["day"])
        self.slot = int(data["round"])
        self.id = int(data["id"])


class Agent(object):
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
        api_key: str = "NULL",
    ):
        """
        Initialize the Agent object.

        :param name: the name of the agent
        :param email: the email of the agent
        :param pwd: the password of the agent
        :param age: the age of the agent
        :param interests: the interests of the agent
        :param leaning: the leaning of the agent
        :param ag_type: the type of the agent
        :param load: whether to load the agent from file or not
        :param recsys: the content recommendation system
        :param frecsys: the follow recommendation system
        :param config: the configuration dictionary
        :param big_five: the big five personality traits
        :param language: the language of the agent
        :param owner: the owner of the agent
        :param education_level: the education level of the agent
        :param joined_on: the joined on date of the agent
        :param round_actions: the number of daily actions
        :param gender: the agent gender
        :param nationality: the agent nationality
        :param api_key: the LLM server api key, default is NULL (self-hosted)
        """
        self.emotions = config["posts"]["emotions"]
        self.base_url = config["servers"]["api"]
        self.llm_base = config["servers"]["llm"]
        self.content_rec_sys_name = None
        self.follow_rec_sys_name = None
        self.name = name
        self.email = email

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

            self.__register()
            try:
                res = json.loads(self.__get_user())
                self.user_id = int(res["id"])
            except:
                pass

        else:
            us = json.loads(self.__get_user())
            self.user_id = us["id"]
            self.type = us["user_type"]
            self.age = us["age"]
            self.interests = us["interests"]
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
            self.nationality = us["nationality"]

        config_list = {
            "model": f"{self.type}",
            "base_url": self.llm_base,
            "timeout": 10000,
            "api_type": "open_ai",
            "api_key": api_key,
            "price": [0, 0],
        }

        self.llm_config = {
            "config_list": [config_list],
            "seed": np.random.randint(0, 100000),
            "max_tokens": -1,  # max response length, -1 no limits. Imposing limits may lead to truncated responses
            "temperature": 1.5,
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

            api_url = f"{self.base_url}update_user"

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

            api_url = f"{self.base_url}update_user"

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
        res = json.loads(self._check_credentials())
        if res["status"] == 404:
            raise Exception("User not found")
        api_url = f"{self.base_url}get_user"

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
        api_url = f"{self.base_url}user_exists"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        params = {"name": self.name, "email": self.email}
        st = json.dumps(params)
        response = post(f"{api_url}", headers=headers, data=st)
        return response.__dict__["_content"].decode("utf-8")

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
                "interests": self.interests,
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
                "joined_on": self.joined_on,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/register"
        post(f"{api_url}", headers=headers, data=st)

    def post(self, tid):
        """
        Post a message to the service.

        :param tid: the round id
        """

        interest = np.random.choice(self.interests, np.random.randint(1, 3))

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay"], interest=interest
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.prompts["handler_instructions"],
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_post"]),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        try:
            emotion_eval = [
                e.strip()
                for e in emotion_eval.replace("'", "")
                .replace('"', "")
                .split(":")[-1]
                .split("[")[1]
                .split("]")[0]
                .split(",")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []

        post_text = u2.chat_messages[u1][-2]["content"]

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
            }
        )

        u1.reset()
        u2.reset()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/post"
        post(f"{api_url}", headers=headers, data=st)

    def news(self, tid, article, website):
        """
        Post a message to the service.

        :param tid: the round id
        :param article: the article
        :param website: the website
        """

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_simple"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_news"], website=website, article=article
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        try:
            emotion_eval = [
                e.strip()
                for e in emotion_eval.replace("'", "")
                .replace('"', "")
                .split(":")[-1]
                .split("[")[1]
                .split("]")[0]
                .split(",")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []

        post_text = u2.chat_messages[u1][-2]["content"]

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
                "title": article.title,
                "summary": article.summary,
                "link": article.link,
                "published": article.published,
                "publisher": website.name,
                "rss": website.rss,
                "leaning": website.leaning,
                "country": website.country,
                "language": website.language,
                "category": website.category,
                "fetched_on": website.last_fetched,
            }
        )

        u1.reset()
        u2.reset()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/news"
        post(f"{api_url}", headers=headers, data=st)

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

    def comment(self, post_id: int, tid, max_length_threads=None):
        """
        Generate a comment to an existing post

        :param post_id: the post id
        :param tid: the round id
        :param max_length_threads: the maximum length of the thread to read for context
        """

        conversation = self.__get_thread(post_id, max_tweets=max_length_threads)
        conv = "".join(conversation)

        interest = np.random.choice(self.interests, np.random.randint(1, 3))

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["agent_roleplay_comments_share"], interest=interest
            ),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(self.prompts["handler_comment"], conv=conv),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        try:
            emotion_eval = [
                e.strip()
                for e in emotion_eval.replace("'", "")
                .replace('"', "")
                .split(":")[-1]
                .split("[")[1]
                .split("]")[0]
                .split(",")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []

        post_text = u2.chat_messages[u1][-2]["content"]

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

        res = self.__evaluate_follow(post_text, post_id, "follow", tid)

        # if not followed, test unfollow
        if res is None:
            self.__evaluate_follow(post_text, post_id, "unfollow", tid)

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

        interest = np.random.choice(self.interests, np.random.randint(1, 3))

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["agent_roleplay_comments_share"], interest=interest),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,  # self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions"]),
            max_consecutive_auto_reply=1,
        )

        u2.initiate_chat(
            u1,
            message=self.__effify(
                self.prompts["handler_share"], article=article, post_text=post_text
            ),
            silent=True,
            max_round=1,
        )

        emotion_eval = u2.chat_messages[u1][-1]["content"].lower()
        try:
            emotion_eval = [
                e.strip()
                for e in emotion_eval.replace("'", "")
                .replace('"', "")
                .split(":")[-1]
                .split("[")[1]
                .split("]")[0]
                .split(",")
                if e.strip() in self.emotions
            ]
        except:
            emotion_eval = []

        post_text = u2.chat_messages[u1][-2]["content"]

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
            self.__evaluate_follow(post_text, post_id, flag, tid)
        else:
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/reaction"
        post(f"{api_url}", headers=headers, data=st)

        # evaluate follow only upon explicit request
        if check_follow and flag == "follow":
            self.__evaluate_follow(post_text, post_id, flag, tid)

    def __evaluate_follow(self, post_text, post_id, action, tid):
        """
        Evaluate a follow action.

        :param post_text: the post text
        :param post_id: the post id
        :param action: the action, either follow or unfollow
        :param tid: the round id
        :return: the response from the service
        """

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
            self.follow(post_id=post_id, action=action, tid=tid)
            return action
        else:
            return None

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

    def select_action(self, tid, actions, max_length_thread_reading=5):
        """
        Post a message to the service.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """
        np.random.shuffle(actions)
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
            message=self.__effify(self.prompts["handler_action"], actions=actions),
            silent=True,
            max_round=1,
        )

        text = u1.chat_messages[u2][-1]["content"].replace("!", "")
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

        elif "REPLY" in text.split():
            selected_post = json.loads(self.read_mentions())
            if "status" not in selected_post:
                self.comment(
                    int(selected_post[0]),
                    max_length_threads=max_length_thread_reading,
                    tid=tid,
                )

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

        elif "NEWS" in text.split():
            news, website = self.select_news()
            if not isinstance(news, str):
                self.news(tid=tid, article=news, website=website)

        elif "SHARE" in text.split():
            candidates = json.loads(self.read(article=True))
            if len(candidates) > 0:
                selected_post = random.sample(candidates, 1)
                self.share(int(selected_post[0]), tid=tid)

        elif "FOLLOW" in text.split():
            candidates = self.search_follow()
            if len(candidates) > 0:
                selected = np.random.choice(
                    [int(c) for c in candidates],
                    p=[v for v in candidates.values()],
                    size=1,
                )[0]
                self.follow(tid=tid, target=selected, action="follow")

        return

    def read(self, article=False):
        """
        Read n_posts from the service.

        :param article: whether to read an article or not
        :return: the response from the service
        """
        return self.content_rec_sys.read(self.base_url, article)

    def read_mentions(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.content_rec_sys.read_mentions(self.base_url)

    def search(self):
        """
        Read n_posts from the service.

        :return: the response from the service
        """
        return self.content_rec_sys.search(self.base_url)

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

    def __str__(self):
        """
        Return a string representation of the Agent object.

        :return: the string representation
        """
        return f"Name: {self.name}, Age: {self.age}, Type: {self.type}, Leaning: {self.leaning}, Interests: {self.interests}"

    def __dict__(self):
        """
        Return a dictionary representation of the Agent object.

        :return: the dictionary representation
        """
        return {
            "name": self.name,
            "email": self.email,
            "password": self.pwd,
            "age": self.age,
            "type": self.type,
            "leaning": self.leaning,
            "interests": self.interests,
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
            "joined_on": self.joined_on,
        }


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
