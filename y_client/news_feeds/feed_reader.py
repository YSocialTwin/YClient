import feedparser
import numpy as np
import json
import requests, re
from bs4 import BeautifulSoup
from y_client import content_store
import datetime


class News(object):
    def __init__(self, title, summary, link, published, image_url=None):
        """
        This class represents a news article.

        :param title: the title of the article
        :param summary: the summary of the article
        :param link: the link to the article
        :param published: the date the article was published
        :param image_url: the url of the image in the article
        """
        self.title = title
        self.summary = summary
        self.link = link
        self.published = published
        self.image_url = image_url

    def __str__(self):
        """
        String representation of the news article.
        :return: a string representation of the news article
        """
        return f"Title: {self.title}\nSummary: {self.summary}\nLink: {self.link}\nPublished: {self.published}"

    def __repr__(self):
        """
        Representation of the news article.
        :return: the string representation of the news article
        """
        return self.__str__()

    def to_dict(self):
        """
        Convert the news article to a dictionary.

        :return: the dictionary representation of the news article
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
            "published": self.published,
        }

    def to_json(self):
        """
        Convert the news article to a json string.

        :return: a json string representation of the news article
        """
        return json.dumps(self.to_dict())

    def save(self, name, rss):
        """
        Save the news article to the database.

        :param name: the name of the website
        :param rss: the rss feed of the website
        """
        return content_store.save_article(
            website_name=name,
            rss=rss,
            title=self.title,
            summary=self.summary,
            published=self.published,
            link=self.link,
            image_url=self.image_url,
        )


class NewsFeed(object):
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
        This class represents a news feed.

        :param name: the name of the website
        :param feed_url: the rss feed url
        :param url_site: the website url
        :param category: the category of the website
        :param language: the language of the website
        :param leaning: the political leaning of the website
        :param country: the country of the website
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
        Read the feed and store the news articles.
        """
        today = datetime.datetime.now()
        today_morning = int(today.strftime("%Y%m%d"))

        # get website id
        website = content_store.get_website(name=self.name, rss=self.feed_url)
        articles = [
            article
            for article in content_store.get_recent_articles_for_feed(
                self.name,
                self.feed_url,
                limit=100,
            )
            if article.fetched_on == today_morning
        ]

        if website is not None and len(articles) == 0:
            feed = feedparser.parse(self.feed_url)
            for entry in feed.entries:
                try:
                    art = News(entry.title, entry.summary, entry.link, today_morning)
                    article_row = art.save(name=self.name, rss=self.feed_url)
                    article_id = getattr(article_row, "id", None)

                    # check if there is an image in the article
                    if "media_content" in entry:
                        img = entry.media_content[0]["url"].split("?")[0]
                        if img is not None and article_id is not None:
                            content_store.ensure_article_image(img, article_id)

                    self.news.append(art)
                except:
                    pass
        else:
            for art in articles:
                self.news.append(News(art.title, art.summary, art.link, art.fetched_on))

    def __extract_image_url(self, art):
        """
        Extract the image url from the article.

        :param art:
        :return: img url
        """
        if "media_content" in art:
            image = art.media_content[0]["url"].split("?")[0]
            return image
        return None

    def get_random_news(self):
        """
        Get a random news article from the feed.

        :return: a random news article
        """
        if len(self.news) == 0:
            return "No news available"
        return np.random.choice(self.news)

    def get_news(self):
        """
        Get all the news articles from the feed.
        :return: a list of news articles
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
        return not content_store.website_exists(name, url)

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
                    content_store.ensure_website(
                        name=name,
                        rss=url_feed,
                        country=country,
                        language=language,
                        leaning=leaning,
                        category=category,
                        last_fetched=today_morning,
                    )
                else:
                    web = content_store.get_website(name=name, rss=url_feed)
                    last_fetched = getattr(web, "last_fetched", None)
                    if last_fetched is not None and today_morning > last_fetched:
                        content_store.update_website_last_fetched(
                            name,
                            url_feed,
                            today_morning,
                        )

        elif url_site is not None:
            fex = FeedLinkExtractor(url_site)
            fex.extract_rss_url()
            for rss in fex.get_rss_urls():
                if self.__not_in_db(name, rss):
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

                        content_store.ensure_website(
                            name=name,
                            rss=rss,
                            country=country,
                            language=language,
                            leaning=leaning,
                            category=category,
                            last_fetched=today_morning,
                        )

                    else:
                        web = content_store.get_website(name=name, rss=rss)
                        last_fetched = getattr(web, "last_fetched", None)
                        if last_fetched is not None and today_morning > last_fetched:
                            content_store.update_website_last_fetched(
                                name,
                                rss,
                                today_morning,
                            )
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
