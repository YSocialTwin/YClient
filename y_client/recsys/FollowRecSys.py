"""
Follow Recommendation Systems Module

This module provides various follow recommendation system implementations for
the Y social network simulation. These systems suggest users to follow based
on different network analysis strategies.

Available Strategies:
    - FollowRecSys: Base system (random suggestions)
    - CommonNeighbors: Suggests users with mutual connections
    - Jaccard: Jaccard coefficient-based similarity
    - AdamicAdar: Adamic/Adar index for link prediction
    - PreferentialAttachment: Rich-get-richer recommendation

All systems support political leaning bias to control homophily.
"""

import json
from requests import post


class FollowRecSys(object):
    """
    Base follow recommendation system for suggesting users to follow.
    
    This class provides the interface for fetching follow suggestions from
    the server. Subclasses customize the recommendation strategy by setting
    different mode parameters.
    
    Attributes:
        name (str): Name of the recommendation system
        n_neighbors (int): Number of users to suggest
        params (dict): Parameters sent to the server including:
                      - mode: Recommendation strategy
                      - n_neighbors: Number of suggestions
                      - leaning_biased: Bias towards similar political leaning
                      - user_id: User ID (added when making requests)
    """
    
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Initialize the follow recommendation system.
        
        Args:
            n_neighbors (int, optional): Number of users to suggest. Defaults to 10.
            leaning_bias (int, optional): Political leaning bias factor.
                                         1 = no bias, higher values increase homophily.
                                         Defaults to 1.
        """
        self.name = "FollowRecSys"
        self.n_neighbors = n_neighbors
        self.params = {
            "mode": "random",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }

    def add_user_id(self, uid):
        """
        Set the user ID for subsequent requests.
        
        Args:
            uid (int): User ID to add to request parameters
        """
        self.params["user_id"] = uid

    def follow_suggestions(self, base_url):
        """
        Fetch follow suggestions from the server for a user.
        
        This method queries the server's /follow_suggestions endpoint to get
        users recommended by this system for the specified user.
        
        Args:
            base_url (str): Base URL of the simulation server API
        
        Returns:
            dict: Dictionary containing suggested user IDs and metadata,
                 or empty dict if request fails
        """
        api_url = f"{base_url}/follow_suggestions"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        st = json.dumps(self.params)
        response = post(f"{api_url}", headers=headers, data=st)

        try:
            return response.json()
        except:
            return {}


class CommonNeighbors(FollowRecSys):
    """
    Recommends users with mutual connections (common neighbors).
    
    This strategy suggests users who share many mutual friends with
    the target user, a common friend-of-friend approach.
    """
    
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Initialize common neighbors recommendation system.
        
        Args:
            n_neighbors (int, optional): Number of users to suggest. Defaults to 10.
            leaning_bias (int, optional): Political leaning bias factor. Defaults to 1.
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "CommonNeighbors"
        self.params = {
            "mode": "common_neighbors",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }


class Jaccard(FollowRecSys):
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Jaccard recommendation system.

        :param n_neighbors: the number of neighbors to consider
        :param leaning_bias: the leaning bias, 1 for no bias
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "Jaccard"
        self.params = {
            "mode": "jaccard",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }


class AdamicAdar(FollowRecSys):
    """
    Recommends users using Adamic/Adar index.
    
    This strategy uses the Adamic/Adar index for link prediction,
    which weights common neighbors by their degree (inverse log).
    """
    
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Initialize Adamic/Adar recommendation system.
        
        Args:
            n_neighbors (int, optional): Number of users to suggest. Defaults to 10.
            leaning_bias (int, optional): Political leaning bias factor. Defaults to 1.
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "AdamicAdar"
        self.params = {
            "mode": "adamic_adar",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }


class PreferentialAttachment(FollowRecSys):
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Preferential attachment recommendation system.

        :param n_neighbors: the number of neighbors to consider
        :param leaning_bias: the leaning bias, 1 for no bias
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "PreferentialAttachment"
        self.params = {
            "mode": "preferential_attachment",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }
