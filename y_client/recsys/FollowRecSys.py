import json
from requests import post


class FollowRecSys(object):
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Follow recommendation system.

        :param n_neighbors: the number of neighbors to consider
        :param leaning_bias: the leaning bias, 1 for no bias
        """
        self.name = "random"
        self.n_neighbors = n_neighbors
        self.params = {
            "mode": "random",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }

    def add_user_id(self, uid):
        """
        Add user id to the request.

        :param uid: the user id
        """
        self.params["user_id"] = uid

    def follow_suggestions(self, base_url):
        """
        Follow suggestions for a user.

        :param base_url: the base url of the service
        :return: the response from the service
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
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Common neighbors recommendation system.

        :param n_neighbors: the number of neighbors to consider
        :param leaning_bias: the leaning bias, 1 for no bias
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "common_neighbors"
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
        self.name = "jaccard"
        self.params = {
            "mode": "jaccard",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }


class AdamicAdar(FollowRecSys):
    def __init__(self, n_neighbors=10, leaning_bias=1):
        """
        Adamic Adar recommendation system.

        :param n_neighbors: the number of neighbors to consider
        :param leaning_bias: the leaning bias, 1 for no bias
        """
        super().__init__(n_neighbors, leaning_bias)
        self.name = "adamic_adar"
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
        self.name = "preferential_attachment"
        self.params = {
            "mode": "preferential_attachment",
            "n_neighbors": n_neighbors,
            "leaning_biased": leaning_bias,
        }
