"""
Recommendation Systems Module

This module provides recommendation system implementations for the Y social network.
It includes content-based recommendation for posts/articles and follow recommendation
for suggesting users to follow.

Exports:
    - ContentRecSys: Content recommendation system for posts and articles
    - FollowRecSys: Follow recommendation system for user connections
"""

from .ContentRecSys import *
from .FollowRecSys import *
