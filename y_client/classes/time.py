import json
from requests import get, post

__all__ = ["SimulationSlot"]


class SimulationSlot(object):
    def __init__(self, config):
        """
        Initialize the SimulationSlot object.

        :param config: the configuration dictionary
        """
        self.base_url = config["servers"]["api"]

        api_url = f"{self.base_url}current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]

    def get_current_slot(self):
        """
        Get the current slot.

        :return: the current slot, day and id
        """

        api_url = f"{self.base_url}current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]

        return self.id, self.day, self.slot

    def increment_slot(self):
        """
        Update the current slot.
        """
        api_url = f"{self.base_url}update_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if self.slot < 23:
            slot = self.slot + 1
            day = self.day
        else:
            slot = 0
            day = self.day + 1

        _, day_c, slot_c = self.get_current_slot()

        if day >= day_c or slot > slot_c:
            params = {"day": day, "round": slot}
            st = json.dumps(params)
            response = post(f"{api_url}", headers=headers, data=st)
            data = json.loads(response.__dict__["_content"].decode("utf-8"))

            self.day = int(data["day"])
            self.slot = int(data["round"])
            self.id = int(data["id"])
