import json
from requests import post


class ContentRecSys(object):
    def __init__(self, n_posts=10, visibility_rounds=36):
        self.name = "random"
        self.params = {
            "limit": n_posts,
            "mode": "default",
            "visibility_rounds": visibility_rounds,
        }

    def add_user_id(self, uid):
        self.params["uid"] = uid

    def read(self, base_url, articles=False):
        """
        Read n_posts from the service.

        """
        api_url = f"{base_url}/read"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if articles:
            self.params["articles"] = True

        st = json.dumps(self.params)

        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def read_mentions(self, base_url):
        """
        Read n_posts from the service.

        """
        api_url = f"{base_url}/read_mentions"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        st = json.dumps(self.params)
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def search(self, base_url):
        """
        Search for a query.

        """
        api_url = f"{base_url}/search"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        st = json.dumps(self.params)
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")


class ReverseChrono(ContentRecSys):
    def __init__(self, n_posts=10, visibility_rounds=36):
        super(ReverseChrono, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "rchrono"
        self.params = {
            "limit": 10,
            "mode": "rchrono",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoPopularity(ContentRecSys):
    def __init__(self, n_posts=10, visibility_rounds=36):
        super(ReverseChronoPopularity, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "rchrono_popularity"
        self.params = {
            "limit": 10,
            "mode": "rchrono_popularity",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoFollowers(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        super(ReverseChronoFollowers, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "rchrono_followers"
        self.params = {
            "limit": 10,
            "followers_ratio": followers_ratio,
            "mode": "rchrono_followers",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoFollowersPopularity(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        super(ReverseChronoFollowersPopularity, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "rchrono_followers_popularity"
        self.params = {
            "limit": 10,
            "followers_ratio": followers_ratio,
            "mode": "rchrono_followers_popularity",
            "visibility_rounds": visibility_rounds,
        }
