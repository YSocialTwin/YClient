from y_client.classes.base_agent import Agent
from y_client.news_feeds.client_modals import Websites, session
from y_client.news_feeds.feed_reader import NewsFeed
from requests import post
from autogen import AssistantAgent
import json
import re


class PageAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feed_url = kwargs.get("feed_url")
        self.name = kwargs.get("name")

    def select_action(self, tid, actions, max_length_thread_reading=5):
        """
        Post a message to the service.

        :param actions: The list of actions to select from.
        :param tid: The time id.
        :param max_length_thread_reading: The maximum length of the thread to read.
        """

        # a page can only post news
        news, website = self.select_news()
        if not isinstance(news, str):
            self.news(tid=tid, article=news, website=website)

        return

    def select_news(self):
        """
        Select a news article from the service.

        :return: the response from the service
        """

        # Select websites with the same name of the page
        website = session.query(Websites).filter(Websites.name == self.name).first()

        if website is None:
            return "", ""

        # Select a random article
        website_feed = NewsFeed(website.name, website.rss)
        website_feed.read_feed()
        article = website_feed.get_random_news()
        return article, website

    def comment(self, post_id: int, tid, max_length_threads=None):
        return

    def reply(self, tid: int, max_length_thread_reading: int = 5):
        return

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
            system_message=self.__effify(self.prompts["page_roleplay"]),
            max_consecutive_auto_reply=1,
        )

        u2 = AssistantAgent(
            name=f"Handler",
            llm_config=self.llm_config,
            system_message=self.__effify(self.prompts["handler_instructions_topics"]),
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

        topic_eval = u2.chat_messages[u1][-1]["content"]

        topics = re.findall(r"[#T]: \w+ \w+", topic_eval)
        topics = [x.split(": ")[1] for x in topics if "Topic" not in x]

        post_text = u2.chat_messages[u1][-2]["content"]
        post_text = post_text.replace(f"@{self.name}", "")

        hashtags = self.__extract_components(post_text, c_type="hashtags")
        mentions = self.__extract_components(post_text, c_type="mentions")

        st = json.dumps(
            {
                "user_id": self.user_id,
                "tweet": post_text.replace('"', ""),
                "emotions": [],
                "hashtags": hashtags,
                "mentions": mentions,
                "tid": tid,
                "title": article.title,
                "summary": article.summary,
                "link": article.link,
                "publisher": website.name,
                "rss": website.rss,
                "leaning": website.leaning,
                "country": website.country,
                "language": website.language,
                "category": website.category,
                "fetched_on": website.last_fetched,
                "topics": topics,
            }
        )

        u1.reset()
        u2.reset()

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        api_url = f"{self.base_url}/news"
        res = post(f"{api_url}", headers=headers, data=st)
        return res

    def __effify(self, non_f_str: str, **kwargs):
        """
        Effify the string.

        :param non_f_str: the string to effify
        :param kwargs: the keyword arguments
        :return: the effified string
        """
        kwargs["self"] = self
        return eval(f'f"""{non_f_str}"""', kwargs)

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

        # interests = self.__get_interests(-1)

        return {
            "name": self.name,
            "email": self.email,
            "password": self.pwd,
            "age": self.age,
            "type": self.type,
            "leaning": self.leaning,
            "interests": [],
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
            "feed_url": self.feed_url,
        }

