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

import numpy as np
from autogen import AssistantAgent
from faker import Faker
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
from y_client.classes.base_agent import Agent

__all__ = ["FakeAgent"]


class FakeAgent(Agent):

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
        super().__init__(name=name, email=email, pwd=pwd, age=age, interests=interests, leaning=leaning, ag_type=ag_type, load=load, recsys=recsys,
                       frecsys=frecsys, config=config, big_five=big_five, language=language, owner=owner, education_level=education_level, joined_on=joined_on,
                       round_actions=round_actions, gender=gender, nationality=nationality, toxicity=toxicity, api_key=api_key, is_page=is_page,
                       daily_activity_level=daily_activity_level, profession=profession, opinions=opinions, archetype=archetype, *args, **kwargs)

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

    @log_execution_time
    def post(self, tid):
        """
        Post a message to the service.

        :param tid: the round id
        """

        # obtain the most recent (and frequent) interests of the agent
        interests, interests_id = self.__get_interests(tid)

        post_text = "sample post"

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        st = json.dumps(
            {
                "user_id": self.user_id,
                "tweet": post_text,
                "emotions": None,
                "hashtags": None,
                "mentions": None,
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

        post_text = "comment"  # fake comment

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text,
                "emotions": None,
                "hashtags": None,
                "mentions": None,
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
        if self.opinions is not None:
            self.new_opinions(post_id, tid, "")

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

        post_text = "share"  # fake text

        st = json.dumps(
            {
                "user_id": self.user_id,
                "post_id": post_id,
                "text": post_text.replace('"', ""),
                "emotions": None,
                "hashtags": None,
                "mentions": None,
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

        faker = Faker()
        dcision = faker.random_element(["YES", "NO"])

        if dcision == "YES":
            st = json.dumps(
                {
                    "user_id": self.user_id,
                    "post_id": post_id,
                    "type": "like",
                    "tid": tid,
                }
            )
            flag = "follow"

        elif dcision == "NO":
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

        faker = Faker()
        decision = faker.random_element(["YES", "NO"])

        if decision == "YES":
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

        faker = Faker()
        decisions = faker.random_element(["RIGHT", "LEFT", "NONE"])

        data = {
            "user_id": self.user_id,
            "post_id": post_id,
            "content_type": "Post",
            "tid": tid,
            "content_id": post_id,
        }

        if decisions == "RIGHT":
            data["vote"] = "R"
            st = json.dumps(data)

        elif decisions == "LEFT":
            data["vote"] = "D"
            st = json.dumps(data)

        elif decisions == "NONE":
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

        faker = Faker()
        action = faker.random_element(actions)

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
                    # an = Annotator(config=self.llm_v_config)
                    description = "image description"  # an.annotate(image.url)

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

        post_text = "comment"

        # avoid posting empty messages
        if len(post_text) < 3:
            return

        st = json.dumps(
            {
                "user_id": self.user_id,
                "text": post_text.replace('"', "")
                .replace(f"{self.name}", "")
                .replace(":", "")
                .replace("*", ""),
                "emotions": None,
                "hashtags": None,
                "tid": tid,
                "image_url": image.url,
                "image_description": image.description,
                "article_id": article_id,
            }
        )

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{self.base_url}/comment_image"
        post(f"{api_url}", headers=headers, data=st)

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
            "archetype": self.archetype
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
