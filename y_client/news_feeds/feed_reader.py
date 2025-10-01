"""
Feed Reader Module

This module provides classes for reading, parsing, and managing RSS news feeds
in the Y social network simulation. It handles fetching articles from RSS feeds,
storing them in a database, and providing access to news content for page agents.

Classes:
    - News: Represents a single news article
    - NewsFeed: RSS feed reader and parser for a single news source
    - Feeds: Collection manager for multiple news feeds
    - FeedLinkExtractor: Utility to discover RSS feed URLs from website pages
"""

import feedparser
import numpy as np
import json
import requests, re
from bs4 import BeautifulSoup

try:
    from .client_modals import Websites, Articles, Images, session
except:
    from y_client.clients.client_web import session
    from .client_modals import Websites, Articles, Images
import datetime


class News(object):
    """
    Represents a single news article with metadata.
    
    This class encapsulates a news article's essential information including
    title, summary, link, publication date, and optional image URL.
    
    Attributes:
        title (str): Article title
        summary (str): Article summary/description
        link (str): URL to the full article
        published (int): Publication date (YYYYMMDD format)
        image_url (str, optional): URL of associated image
    """
    
    def __init__(self, title, summary, link, published, image_url=None):
        """
        Initialize a News article object.
        
        Args:
            title (str): The title of the article
            summary (str): The summary or description of the article
            link (str): URL to the full article
            published (int): Publication date in YYYYMMDD format
            image_url (str, optional): URL of the article's image. Defaults to None.
        """
        self.title = title
        self.summary = summary
        self.link = link
        self.published = published
        self.image_url = image_url

    def __str__(self):
        """
        Return a human-readable string representation of the article.
        
        Returns:
            str: Formatted string with title, summary, link, and publication date
        """
        return f"Title: {self.title}\nSummary: {self.summary}\nLink: {self.link}\nPublished: {self.published}"

    def __repr__(self):
        """
        Return a representation of the article (same as __str__).
        
        Returns:
            str: String representation of the article
        """
        return self.__str__()

    def to_dict(self):
        """
        Convert the article to a dictionary.
        
        Returns:
            dict: Dictionary with keys: title, summary, link, published
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
            "published": self.published,
        }

    def to_json(self):
        """
        Convert the article to a JSON string.
        
        Returns:
            str: JSON string representation of the article
        """
        return json.dumps(self.to_dict())

    def save(self, name, rss):
        """
        Save the article to the database.
        
        This method stores the article in the Articles table and its associated
        image (if present) in the Images table. It avoids duplicate entries by
        checking if the article link already exists.
        
        Args:
            name (str): Name of the website/feed
            rss (str): RSS feed URL of the website
        
        Side effects:
            Creates entries in Articles and Images tables if they don't exist
        """
        website_id = (
            session.query(Websites)
            .filter(Websites.name == name, Websites.rss == rss)
            .first()
            .id
        )
        # check if article exists
        if session.query(Articles).filter(Articles.link == self.link).first() is None:
            art = Articles(
                title=self.title,
                summary=self.summary,
                website_id=website_id,
                fetched_on=self.published,
                link=self.link,
            )
            session.add(art)
            session.commit()

        # get the article id
        article_id = (
            session.query(Articles).filter(Articles.link == self.link).first().id
        )

        if self.image_url is not None:
            img = Images(url=self.image_url, article_id=article_id)
            session.add(img)
            session.commit()


class NewsFeed(object):
    """
    RSS feed reader and parser for a single news source.
    
    This class handles reading and parsing RSS feeds, storing articles in
    the database, and providing access to news articles. It caches articles
    from the current day to avoid redundant parsing.
    
    Attributes:
        feed_url (str): RSS feed URL
        name (str): Name of the news source
        url_site (str): Main website URL
        category (str): Content category (e.g., "politics", "tech")
        language (str): Primary language
        leaning (str): Political leaning
        country (str): Country of origin
        news (list): List of News objects fetched from the feed
    """
    
    def __init__(
        self,
        name,
        feed_url,
        url_site=None,
        category=None,
        language=None,
        leaning=None,
        country=None,
    ):
        """
        Initialize a NewsFeed object for a news source.
        
        Args:
            name (str): Name of the news source/website
            feed_url (str): RSS feed URL to parse
            url_site (str, optional): Main website URL. Defaults to None.
            category (str, optional): Content category. Defaults to None.
            language (str, optional): Primary language. Defaults to None.
            leaning (str, optional): Political leaning. Defaults to None.
            country (str, optional): Country of origin. Defaults to None.
        """
        self.feed_url = feed_url
        self.name = name
        self.url_site = url_site
        self.category = category
        self.language = language
        self.leaning = leaning
        self.country = country
        self.news = []

    def read_feed(self):
        """
        Fetch and parse articles from the RSS feed.
        
        This method reads the RSS feed, parses all entries, and stores them
        in the database. If articles from today are already in the database,
        it loads them from there instead of re-parsing the feed.
        
        Side effects:
            - Populates self.news with News objects
            - Creates entries in Articles and Images tables
            - Updates website's last_fetched timestamp
        """
        today = datetime.datetime.now()
        today_morning = int(today.strftime("%Y%m%d"))

        # get website id
        website_id = (
            session.query(Websites)
            .filter(Websites.name == self.name, Websites.rss == self.feed_url)
            .first()
            .id
        )
        # get all articles from this website from today
        articles = (
            session.query(Articles)
            .filter(
                Articles.website_id == website_id, Articles.fetched_on == today_morning
            )
            .all()
        )

        if len(articles) == 0:
            feed = feedparser.parse(self.feed_url)
            for entry in feed.entries:
                try:
                    art = News(entry.title, entry.summary, entry.link, today_morning)
                    art.save(name=self.name, rss=self.feed_url)

                    # get article id to save image
                    article_id = (
                        session.query(Articles)
                        .filter(Articles.link == entry.link)
                        .first()
                        .id
                    )

                    # check if there is an image in the article
                    if "media_content" in entry:
                        img = entry.media_content[0]["url"].split("?")[0]
                        if img is not None:
                            # check if image is already in the database
                            if (
                                session.query(Images).filter(Images.url == img).first()
                                is None
                            ):
                                img = Images(url=img, article_id=article_id)
                                session.add(img)
                                session.commit()

                    self.news.append(art)
                except:
                    pass
        else:
            for art in articles:
                self.news.append(News(art.title, art.summary, art.link, art.fetched_on))

    def __extract_image_url(self, art):
        """
        Extract image URL from an RSS feed entry.
        
        Args:
            art: RSS feed entry object (from feedparser)
        
        Returns:
            str or None: Image URL if found, None otherwise
        """
        if "media_content" in art:
            image = art.media_content[0]["url"].split("?")[0]
            return image
        return None

    def get_random_news(self):
        """
        Select a random article from the feed.
        
        Returns:
            News or str: Random News object from the feed, or "No news available"
                        if the feed is empty
        """
        if len(self.news) == 0:
            return "No news available"
        return np.random.choice(self.news)

    def get_news(self):
        """
        Get all articles from the feed.
        
        Returns:
            list: List of News objects
        """
        return self.news

    def to_dict(self):
        """
        Convert the news feed to a dictionary.

        :return: the dictionary representation of the news feed
        """
        return {
            "name": self.name,
            "feed_url": self.feed_url,
            "url_site": self.url_site,
            "category": self.category,
            "language": self.language,
            "leaning": self.leaning,
            "country": self.country,
            "news": [n.to_dict() for n in self.news],
        }

    def to_json(self):
        """
        Convert the news feed to a json string.

        :return: a json string representation of the news feed
        """
        return json.dumps(self.to_dict())


class Feeds(object):
    def __init__(self):
        """
        This class represents a collection of news feeds.
        """
        self.feeds = []

    @staticmethod
    def __not_in_db(name: str, url: str) -> object:
        """
        Check if the feed is not in the database.

        :param name: the name of the website
        :param url: the rss feed url
        :return: whether the feed is not in the database
        """
        res = (
            session.query(Websites)
            .filter(Websites.name == name, Websites.rss == url)
            .first()
        )
        return res is None

    def add_feed(
        self,
        name,
        url_site=None,
        url_feed=None,
        category=None,
        language=None,
        leaning=None,
        country=None,
    ):
        """
        Add a feed to the collection.

        :param name: the name of the website
        :param url_site: the website url
        :param url_feed: the rss feed url
        :param category: the category of the website
        :param language: the language of the website
        :param leaning: the political leaning of the website
        :param country: the country of the website
        """
        today = datetime.datetime.now()
        today_morning = int(today.strftime("%Y%m%d"))

        if url_feed is not None:
            if self.__not_in_db(name, url_feed):
                if self.__validate_feed(url_feed):
                    self.feeds.append(
                        NewsFeed(
                            name,
                            url_feed,
                            url_site,
                            category,
                            language,
                            leaning,
                            country,
                        )
                    )

                    # check if website exists
                    web = Websites(
                        name=name,
                        rss=url_feed,
                        country=country,
                        language=language,
                        leaning=leaning,
                        category=category,
                        last_fetched=today_morning,
                    )
                    session.add(web)
                    session.commit()
                else:
                    last_fetched = (
                        session.query(Websites)
                        .filter(Websites.name == name, Websites.rss == url_feed)
                        .first()
                        .last_fetched
                    )
                    if today_morning > last_fetched:
                        session.query(Websites).filter(
                            Websites.name == name, Websites.rss == url_feed
                        ).update({"last_fetched": today_morning})
                        session.commit()

        elif url_site is not None:
            fex = FeedLinkExtractor(url_site)
            fex.extract_rss_url()
            for rss in fex.get_rss_urls():
                if self.__not_in_db(name, url_feed):
                    if self.__validate_feed(rss):
                        self.feeds.append(
                            NewsFeed(
                                name,
                                rss,
                                url_site,
                                category,
                                language,
                                leaning,
                                country,
                            )
                        )

                        web = Websites(
                            name=name,
                            rss=url_feed,
                            country=country,
                            language=language,
                            leaning=leaning,
                            category=category,
                            last_fetched=today_morning,
                        )
                        session.add(web)
                        session.commit()

                    else:
                        last_fetched = (
                            session.query(Websites)
                            .filter(Websites.name == name, Websites.rss == url_feed)
                            .first()
                            .last_fetched
                        )
                        if today_morning > last_fetched:
                            session.query(Websites).filter(
                                Websites.name == name, Websites.rss == url_feed
                            ).update({"last_fetched": today_morning})
                            session.commit()
        else:
            print("Please provide a feed url or a site url")

    def get_feeds(self):
        """
        Get all the feeds in the collection.

        :return: a list of feeds
        """
        return self.feeds

    @staticmethod
    def __validate_feed(url):
        """
        Validate the rss feed.

        :param url: the rss feed url
        :return: whether the feed is valid
        """
        try:
            feedparser.parse(url)
            return True
        except:
            return False


class FeedLinkExtractor(object):
    def __init__(self, url):
        """
        This class extracts rss feed urls from a website.

        :param url: the website url
        """
        self.url = url
        self.rss_urls = []

    def extract_rss_url(self):
        """
        Extract (or at least tries to) the rss feed urls from the website.
        """
        try:
            page = requests.get(self.url, timeout=5).text
            soup = BeautifulSoup(page, features="html.parser")

            for e in soup.select(
                'a[href*="rss"],a[href*="/feed"],a:-soup-contains-own("RSS")'
            ):
                if e.get("href").startswith("/"):
                    url = self.url.strip("/") + e.get("href")
                else:
                    url = e.get("href")

                base_url = re.search(
                    "^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)", url
                ).group(0)
                r = requests.get(url)
                soup = BeautifulSoup(r.text, features="html.parser")

                for e1 in soup.select(
                    '[type="application/rss+xml"],a[href*=".rss"],a[href$="feed"]'
                ):
                    if e1.get("href").startswith("/"):
                        rss = base_url + e1.get("href")
                    else:
                        rss = e1.get("href")
                    if "xml" in requests.get(rss).headers.get("content-type"):
                        self.rss_urls.append(rss)
        except:
            pass

    def get_rss_urls(self):
        """
        Get the extracted rss feed urls.

        :return: the extracted rss feed urls
        """
        return self.rss_urls

    def to_dict(self):
        """
        Convert the rss feed urls to a dictionary.

        :return: the dictionary representation of the rss feed urls
        """
        return {"rss_urls": self.rss_urls}

    def to_json(self):
        """
        Convert the rss feed urls to a json string.

        :return: the json string representation of the rss feed urls
        """
        return json.dumps(self.to_dict())
