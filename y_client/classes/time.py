"""
Time Management Module

This module provides time management functionality for the Y social network simulation.
It handles the simulation clock, tracking days and time slots (hours), and synchronizing
with the server's time state.
"""

import json

from requests import get, post

__all__ = ["SimulationSlot"]


class SimulationSlot(object):
    """
    Manages simulation time by tracking days and hourly time slots.
    
    This class synchronizes with the server to maintain the current simulation time,
    which is divided into days (24-hour periods) and slots (individual hours).
    It provides methods to query and increment the simulation time.
    
    Attributes:
        base_url (str): Base URL for the simulation server API
        day (int): Current simulation day (0-indexed)
        slot (int): Current time slot within the day (0-23, representing hours)
        id (int): Unique identifier for the current time point
    """
    
    def __init__(self, config):
        """
        Initialize the SimulationSlot object and sync with server time.
        
        Args:
            config (dict): Configuration dictionary containing:
                - servers.api (str): Base URL for the simulation server API
        """
        self.base_url = config["servers"]["api"].rstrip("/")

        api_url = f"{self.base_url}/current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]

    def get_current_slot(self):
        """
        Query and update the current simulation time from the server.
        
        This method fetches the current time state from the simulation server
        and updates the local time attributes (day, slot, id).
        
        Returns:
            tuple: A tuple containing (id, day, slot) representing:
                - id (int): Unique identifier for the current time point
                - day (int): Current simulation day
                - slot (int): Current time slot (hour) within the day
        """

        api_url = f"{self.base_url}/current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]

        return self.id, self.day, self.slot

    def increment_slot(self):
        """
        Advance the simulation time by one slot (hour).
        
        This method increments the simulation time by one slot. If the current slot
        is 23 (last hour of the day), it advances to day+1, slot 0. The method
        only updates the server if the new time is ahead of the current server time,
        preventing backwards time travel.
        
        The time wraps around at slot 23: (day=0, slot=23) -> (day=1, slot=0)
        
        Side effects:
            Updates self.day, self.slot, and self.id with the new time values
            after successfully incrementing the server time.
        """
        api_url = f"{self.base_url}/update_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if self.slot < 23:
            slot = self.slot + 1
            day = self.day
        else:
            slot = 0
            day = self.day + 1

        _, day_c, slot_c = self.get_current_slot()

        if day > day_c or (day == day_c and slot > slot_c):
            params = {"day": day, "round": slot}
            st = json.dumps(params)
            response = post(f"{api_url}", headers=headers, data=st)
            data = json.loads(response.__dict__["_content"].decode("utf-8"))

            self.day = int(data["day"])
            self.slot = int(data["round"])
            self.id = int(data["id"])
