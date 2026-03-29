"""
Content Recommendation Systems Module

This module provides various content recommendation system implementations for
the Y social network simulation. These systems determine which posts appear
in a user's feed based on different ranking strategies.

Available Strategies:
    - ContentRecSys: Base recommendation system (default chronological)
    - ReverseChrono: Simple reverse chronological ordering
    - ReverseChronoPopularity: Chronological with popularity boost
    - ReverseChronoFollowers: Prioritizes content from followed users
    - ReverseChronoFollowersPopularity: Follows + popularity
    - ReverseChronoComments: Prioritizes highly commented posts
    - CommonInterests: Recommends based on shared interests
    - CommonUserInterests: User-based interest matching
    - SimilarUsersReactions: Recommends based on similar users' reactions
    - SimilarUsersPosts: Recommends based on similar users' posting patterns

All classes inherit from ContentRecSys and communicate with the server API
to fetch recommended posts.
"""

import json

from requests import post


class ContentRecSys(object):
    """
    Base content recommendation system for post feeds.
    
    This class provides the interface for fetching recommended posts from
    the server. Subclasses customize the recommendation strategy by setting
    different mode parameters.
    
    Attributes:
        name (str): Name of the recommendation system
        params (dict): Parameters sent to the server including:
                      - limit: Number of posts to fetch
                      - mode: Recommendation strategy
                      - visibility_rounds: How long posts remain visible
                      - uid: User ID (added when making requests)
    """
    
    def __init__(self, n_posts=10, visibility_rounds=36):
        """
        Initialize the content recommendation system.
        
        Args:
            n_posts (int, optional): Number of posts to recommend. Defaults to 10.
            visibility_rounds (int, optional): Number of time slots posts remain visible
                                              (typically hours). Defaults to 36.
        """
        self.name = "ContentRecSys"
        self.params = {
            "limit": n_posts,
            "mode": "default",
            "visibility_rounds": visibility_rounds,
        }

    def add_user_id(self, uid):
        """
        Set the user ID for subsequent requests.
        
        Args:
            uid (int): User ID to add to request parameters
        """
        self.params["uid"] = uid

    def read(self, base_url, user_id, articles=False):
        """
        Fetch recommended posts from the server for a user.
        
        This method queries the server's /read endpoint to get posts
        recommended by this system for the specified user.
        
        Args:
            base_url (str): Base URL of the simulation server API
            user_id (int): User ID to fetch recommendations for
            articles (bool, optional): Whether to include news articles.
                                      Defaults to False.
        
        Returns:
            str: JSON string containing recommended posts
        """
        api_url = f"{base_url}/read"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if articles:
            self.params["articles"] = True

        self.params["uid"] = user_id

        st = json.dumps(self.params)

        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def read_mentions(self, base_url):
        """
        Fetch posts that mention the user.
        
        Args:
            base_url (str): Base URL of the simulation server API
        
        Returns:
            str: JSON string containing posts that mention the user
        """
        api_url = f"{base_url}/read_mentions"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        st = json.dumps(self.params)
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")

    def search(self, base_url):
        """
        Search for posts matching query criteria.
        
        Args:
            base_url (str): Base URL of the simulation server API
        
        Returns:
            str: JSON string containing search results
        
        Note:
            Query parameters should be set in self.params before calling
        """
        api_url = f"{base_url}/search"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        st = json.dumps(self.params)
        response = post(f"{api_url}", headers=headers, data=st)

        return response.__dict__["_content"].decode("utf-8")


class ReverseChrono(ContentRecSys):
    """
    Simple reverse chronological feed (newest posts first).
    
    This recommendation system orders posts by recency without any
    personalization or filtering.
    """
    
    def __init__(self, n_posts=10, visibility_rounds=36):
        """
        Initialize reverse chronological recommendation system.
        
        Args:
            n_posts (int, optional): Number of posts to recommend. Defaults to 10.
            visibility_rounds (int, optional): Post visibility duration. Defaults to 36.
        """
        super(ReverseChrono, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "ReverseChrono"
        self.params = {
            "limit": 10,
            "mode": "rchrono",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoPopularity(ContentRecSys):
    def __init__(self, n_posts=10, visibility_rounds=36):
        """
        Reverse chronological popularity content recommendation system.

        :param n_posts: the number of posts to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(ReverseChronoPopularity, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "ReverseChronoPopularity"
        self.params = {
            "limit": 10,
            "mode": "rchrono_popularity",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoFollowers(ContentRecSys):
    """
    Chronological feed prioritizing posts from followed users.
    
    This system shows a mix of posts from followed users and the general
    network, with a configurable ratio.
    """
    
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Initialize followers-prioritizing recommendation system.
        
        Args:
            n_posts (int, optional): Number of posts to recommend. Defaults to 10.
            followers_ratio (float, optional): Proportion of posts from followed users
                                              (0.0-1.0). Defaults to 0.6.
            visibility_rounds (int, optional): Post visibility duration. Defaults to 36.
        """
        super(ReverseChronoFollowers, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "ReverseChronoFollowers"
        self.params = {
            "limit": 10,
            "followers_ratio": followers_ratio,
            "mode": "rchrono_followers",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoFollowersPopularity(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Reverse chronological followers popularity content recommendation system.

        :param n_posts: the number of posts to recommend
        :param followers_ratio: the ratio posts from followers to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(ReverseChronoFollowersPopularity, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "ReverseChronoFollowersPopularity"
        self.params = {
            "limit": 10,
            "followers_ratio": followers_ratio,
            "mode": "rchrono_followers_popularity",
            "visibility_rounds": visibility_rounds,
        }


class ReverseChronoComments(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Reverse chronological most commented content recommendation system.

        :param n_posts: the number of posts to recommend
        :param followers_ratio: the ratio of posts from followers to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(ReverseChronoComments, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "ReverseChronoComments"
        self.params = {
            "limit": n_posts,
            "followers_ratio": followers_ratio,
            "mode": "rchrono_comments",
            "visibility_rounds": visibility_rounds,
        }


class CommonInterests(ContentRecSys):
    """
    Recommends posts matching the user's interests.
    
    This system surfaces posts with topics/hashtags that align with
    the user's declared interests.
    """
    
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Initialize interest-based recommendation system.
        
        Args:
            n_posts (int, optional): Number of posts to recommend. Defaults to 10.
            followers_ratio (float, optional): Proportion from followed users. Defaults to 0.6.
            visibility_rounds (int, optional): Post visibility duration. Defaults to 36.
        """
        super(CommonInterests, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "CommonInterests"
        self.params = {
            "limit": n_posts,
            "followers_ratio": followers_ratio,
            "mode": "common_interests",
            "visibility_rounds": visibility_rounds,
        }


class CommonUserInterests(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Common interests content recommendation system.

        :param n_posts: the number of posts to recommend
        :param followers_ratio: the ratio posts from followers to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(CommonUserInterests, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "CommonUserInterests"
        self.params = {
            "limit": n_posts,
            "followers_ratio": followers_ratio,
            "mode": "common_user_interests",
            "visibility_rounds": visibility_rounds,
        }


class SimilarUsersReactions(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Similar users content recommendation system.

        :param n_posts: the number of posts to recommend
        :param followers_ratio: the ratio posts from followers to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(SimilarUsersReactions, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "SimilarUsersReactions"
        self.params = {
            "limit": n_posts,
            "followers_ratio": followers_ratio,
            "mode": "similar_users",
            "visibility_rounds": visibility_rounds,
        }


class SimilarUsersPosts(ContentRecSys):
    def __init__(self, n_posts=10, followers_ratio=0.6, visibility_rounds=36):
        """
        Similar users content recommendation system.

        :param n_posts: the number of posts to recommend
        :param followers_ratio: the ratio posts from followers to recommend
        :param visibility_rounds: the number of visibility rounds
        """
        super(SimilarUsersPosts, self).__init__(
            n_posts=n_posts, visibility_rounds=visibility_rounds
        )
        self.name = "SimilarUsersPosts"
        self.params = {
            "limit": n_posts,
            "followers_ratio": followers_ratio,
            "mode": "similar_users_posts",
            "visibility_rounds": visibility_rounds,
        }
