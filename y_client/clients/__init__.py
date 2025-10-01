"""
Clients Module

This module provides client implementations for interacting with the Y social network.
It includes base client functionality and specialized web client implementations
with support for pages and news feeds.

Exports:
    - YClientBase: Base client class with core simulation functionality
    - YClientWithPages: Client with support for page agents
    - YClientWeb: Web-based client implementation
"""

try:
    from .client_base import *
    from .client_with_pages import *
except:
    from .client_web import *
