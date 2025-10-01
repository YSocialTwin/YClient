"""
Y Client Package

This package provides the main interfaces and classes for the Y social network simulation client.
It includes agent classes, time management, recommendation systems, and web client implementations.

Main exports:
    - Agent classes (Agent, PageAgent)
    - Time management (SimulationSlot)
    - Recommendation systems (ContentRecSys, FollowRecSys)
    - Web client (YClientWeb)
"""

try:
    from y_client.classes.base_agent import *
    from y_client.classes.page_agent import *
    from y_client.classes.time import *
    from y_client.recsys import *
except:
    from y_client.clients import YClientWeb
