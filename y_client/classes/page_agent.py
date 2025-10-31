"""
Page Agent Module

This module provides the PageAgent class, which represents news page accounts
in the Y social network simulation. Page agents differ from regular agents by
focusing solely on publishing news content from RSS feeds.
"""

import json
import re

from autogen import AssistantAgent
from requests import post
from y_client.classes.base_agent import Agent
from y_client.news_feeds.client_modals import Websites, session
from y_client.news_feeds.feed_reader import NewsFeed


class PageAgent(Agent):
    """
    Specialized agent representing a news page or media outlet.
    
    PageAgent extends the base Agent class to create accounts that publish
    news content from RSS feeds. Unlike regular agents, pages can only perform
    news posting actions and cannot comment or reply to posts.
    
    Attributes:
        feed_url (str): URL of the RSS feed for this page
        name (str): Name of the page/media outlet
        (inherits all other attributes from Agent)
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize a PageAgent instance.
        
        Args:
            *args: Variable length argument list passed to parent Agent class
            **kwargs: Arbitrary keyword arguments, including:
                - feed_url (str): URL of the RSS feed for this page
                - name (str): Name of the page
                Plus all arguments accepted by the parent Agent class
        """
        super().__init__(*args, **kwargs)
        self.feed_url = kwargs.get("feed_url")
        self.name = kwargs.get("name")

    def select_action(self, tid, actions, max_length_thread_reading=5):
        """
        Select and perform the page's action for the current time slot.
        
        For PageAgent, the only action is posting news. This method retrieves
        a news article from the page's RSS feed and posts it to the network.
        
        Args:
            tid (int): Time slot identifier for the current simulation time
            actions (list): List of possible actions (unused for pages, always posts news)
            max_length_thread_reading (int, optional): Maximum thread length (unused for pages).
                                                       Defaults to 5.
        
        Returns:
            None
        """

        # a page can only post news
        news, website = self.select_news()
        if not isinstance(news, str):
            self.news(tid=tid, article=news, website=website)
        return

    def select_news(self):
        """
        Select a random news article from the page's RSS feed.
        
        This method queries the database for the website associated with this page,
        fetches its RSS feed, and selects a random article to post.
        
        Returns:
            tuple: A tuple containing:
                - article (Article or str): The selected article object, or empty string if none found
                - website (Website or str): The website object, or empty string if none found
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
        """
        Comment on a post (disabled for page agents).
        
        PageAgents cannot comment on posts. This method is a no-op override
        of the parent Agent's comment method.
        
        Args:
            post_id (int): ID of the post to comment on (unused)
            tid (int): Time slot identifier (unused)
            max_length_threads (int, optional): Maximum thread length (unused)
        
        Returns:
            None
        """
        return

    def reply(self, tid: int, max_length_thread_reading: int = 5):
        """
        Reply to a comment (disabled for page agents).
        
        PageAgents cannot reply to comments. This method is a no-op override
        of the parent Agent's reply method.
        
        Args:
            tid (int): Time slot identifier (unused)
            max_length_thread_reading (int, optional): Maximum thread length (unused).
                                                       Defaults to 5.
        
        Returns:
            None
        """
        return

    def news(self, tid, article, website):
        """
        Post a news article to the social network.
        
        This method uses LLM agents to generate a post based on a news article,
        extract topics and hashtags, and publish it to the network with full
        metadata including source information and categorization.
        
        The process involves:
        1. Creating a roleplay agent to generate post text from the article
        2. Using a handler agent to extract topics from the content
        3. Parsing hashtags and mentions from the generated text
        4. Posting the news with complete metadata to the server
        
        Args:
            tid (int): Time slot identifier for when the post is created
            article (Article): Article object containing title, summary, link, etc.
            website (Website): Website object with metadata (name, rss, leaning, country, etc.)
        
        Returns:
            Response: HTTP response object from the POST request to the news endpoint
        """

        u1 = AssistantAgent(
            name=f"{self.name}",
            llm_config=self.llm_config,
            system_message=self.__effify(
                self.prompts["page_roleplay"], website=website, article=article
            ),
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
        Convert a non-f-string to an f-string and evaluate it.
        
        This utility method allows dynamic string formatting by converting
        a regular string into an f-string and evaluating it with provided kwargs.
        It automatically adds 'self' to the kwargs for convenience.
        
        Args:
            non_f_str (str): String to convert and evaluate (should contain {var} placeholders)
            **kwargs: Variables to make available during f-string evaluation
        
        Returns:
            str: The evaluated f-string with placeholders replaced by values
        """
        kwargs["self"] = self
        return eval(f'f"""{non_f_str}"""', kwargs)

    def __extract_components(self, text, c_type="hashtags"):
        """
        Extract hashtags or mentions from text using regex patterns.
        
        Args:
            text (str): Text to extract components from
            c_type (str, optional): Type of component to extract.
                                   Options: "hashtags" (extracts #word) or "mentions" (extracts @word).
                                   Defaults to "hashtags".
        
        Returns:
            list: List of extracted components (e.g., ['#python', '#ai'] or ['@user1', '@user2']).
                 Returns empty list if c_type is not recognized.
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
        Return a string representation of the PageAgent.
        
        Returns:
            str: Human-readable string with the agent's name, age, and type
        """
        return f"Name: {self.name}, Age: {self.age}, Type: {self.type}"

    def __dict__(self):
        """
        Return a dictionary representation of the PageAgent.
        
        Returns:
            dict: Dictionary containing all agent attributes including:
                 name, email, password, age, type, leaning, interests,
                 Big Five personality traits (oe, co, ex, ag, ne),
                 recommendation systems, language, owner, education_level,
                 round_actions, gender, nationality, toxicity, joined_on,
                 is_page flag, and feed_url
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
