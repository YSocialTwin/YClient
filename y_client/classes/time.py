"""
Time Management Module

This module provides time management functionality for the Y social network simulation.
It handles the simulation clock, tracking days and time slots (hours), and synchronizing
with the server's time state.
"""

import json
import threading
import time as pytime

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
    
    def __init__(self, config, client_id=None, heartbeat_interval=5.0, poll_interval=0.25):
        """
        Initialize the SimulationSlot object and sync with server time.
        
        Args:
            config (dict): Configuration dictionary containing:
                - servers.api (str): Base URL for the simulation server API
        """
        self.base_url = config["servers"]["api"].rstrip("/")
        self.client_id = str(client_id or "").strip() or "client"
        self.heartbeat_interval = float(heartbeat_interval)
        self.poll_interval = float(poll_interval)
        self._last_heartbeat = 0.0
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None

        api_url = f"{self.base_url}/current_time"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = get(f"{api_url}", headers=headers)
        data = json.loads(response.__dict__["_content"].decode("utf-8"))

        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]
        self.register_client()

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

    def _post_json(self, path, payload):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return post(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=headers,
            data=json.dumps(payload),
        )

    def register_client(self):
        response = self._post_json("/register_client", {"client_id": self.client_id})
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if response.status_code >= 400:
            raise RuntimeError(f"client registration failed: {data}")
        self.day = data["day"]
        self.slot = data["round"]
        self.id = data["id"]
        self._last_heartbeat = pytime.time()
        self._ensure_heartbeat_worker()
        return data

    def _ensure_heartbeat_worker(self):
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            name=f"SimulationSlotHeartbeat-{self.client_id}",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _heartbeat_worker(self):
        interval = max(0.1, float(self.heartbeat_interval))
        while not self._heartbeat_stop.wait(interval):
            try:
                self.heartbeat(force=True)
            except Exception:
                if self._heartbeat_stop.is_set():
                    return

    def _stop_heartbeat_worker(self):
        self._heartbeat_stop.set()
        worker = self._heartbeat_thread
        if worker and worker.is_alive():
            worker.join(timeout=max(1.0, self.heartbeat_interval))
        self._heartbeat_thread = None

    def heartbeat(self, force=False):
        now = pytime.time()
        if not force and (now - self._last_heartbeat) < self.heartbeat_interval:
            return None
        response = self._post_json("/heartbeat", {"client_id": self.client_id})
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if response.status_code >= 400:
            raise RuntimeError(f"heartbeat failed: {data}")
        self._last_heartbeat = now
        return data

    def maybe_heartbeat(self):
        return self.heartbeat(force=False)

    def complete_client(self):
        try:
            response = self._post_json("/complete_client", {"client_id": self.client_id})
            data = json.loads(response.__dict__["_content"].decode("utf-8"))
            if response.status_code >= 400:
                raise RuntimeError(f"complete_client failed: {data}")
            self.day = data["day"]
            self.slot = data["round"]
            self.id = data["id"]
            return data
        finally:
            self._stop_heartbeat_worker()

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
        current_round_id = int(self.id)
        response = self._post_json(
            "/submit_round",
            {
                "client_id": self.client_id,
                "round_id": current_round_id,
                "day": int(self.day),
                "round": int(self.slot),
            },
        )
        data = json.loads(response.__dict__["_content"].decode("utf-8"))
        if response.status_code >= 400 and data.get("error") != "round_mismatch":
            raise RuntimeError(f"submit_round failed: {data}")

        if data.get("error") == "round_mismatch":
            self.day = int(data["day"])
            self.slot = int(data["round"])
            self.id = int(data["id"])
            return

        if data.get("advanced"):
            self.day = int(data["day"])
            self.slot = int(data["round"])
            self.id = int(data["id"])
            return

        while True:
            pytime.sleep(self.poll_interval)
            self.heartbeat(force=True)
            rid, day, slot = self.get_current_slot()
            if int(rid) != current_round_id:
                self.id = int(rid)
                self.day = int(day)
                self.slot = int(slot)
                return
