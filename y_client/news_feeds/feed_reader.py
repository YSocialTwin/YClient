import feedparser
import numpy as np
import json
import requests, re
from bs4 import BeautifulSoup
from .client_modals import Websites, Articles, session
import datetime


class News(object):
    def __init__(self, title, summary, link, published):
        self.title = title
        self.summary = summary
        self.link = link
        self.published = published

    def __str__(self):
        return f"Title: {self.title}\nSummary: {self.summary}\nLink: {self.link}\nPublished: {self.published}"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
            "published": self.published,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def save(self, name, rss):
        website_id = (
            session.query(Websites)
            .filter(Websites.name == name, Websites.rss == rss)
            .first()
            .id
        )
        art = Articles(
            title=self.title,
            summary=self.summary,
            website_id=website_id,
            fetched_on=self.published,
            link=self.link,
        )
        session.add(art)
        session.commit()


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
        self.feed_url = feed_url
        self.name = name
        self.url_site = url_site
        self.category = category
        self.language = language
        self.leaning = leaning
        self.country = country
        self.news = []

    def read_feed(self):
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
                    self.news.append(art)
                except:
                    pass
        else:
            for art in articles:
                self.news.append(News(art.title, art.summary, art.link, art.fetched_on))

    def get_random_news(self):
        if len(self.news) == 0:
            return "No news available"
        return np.random.choice(self.news)

    def get_news(self):
        return self.news

    def to_dict(self):
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
        return json.dumps(self.to_dict())


class Feeds(object):
    def __init__(self):
        self.feeds = []

    @staticmethod
    def __not_in_db(name: str, url: str) -> object:
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
        return self.feeds

    @staticmethod
    def __validate_feed(url):
        try:
            feedparser.parse(url)
            return True
        except:
            return False


class FeedLinkExtractor(object):
    def __init__(self, url):
        self.url = url
        self.rss_urls = []

    def extract_rss_url(self):
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
        return self.rss_urls

    def to_dict(self):
        return {"rss_urls": self.rss_urls}

    def to_json(self):
        return json.dumps(self.to_dict())
