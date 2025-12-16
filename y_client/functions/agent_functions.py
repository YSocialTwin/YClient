"""
Agent Functions Module - CPU-bound Operations

This module contains CPU-bound functions for agent operations that don't require
LLM inference. These functions operate on AgentData instances and can be
efficiently parallelized with Ray for CPU tasks.

Functions are organized by category:
- Network operations (follow, read, search)
- Utility functions (extract components, get user info)
- Data retrieval (get interests, get opinions, get articles)

All functions are designed to be stateless and work with AgentData instances,
making them suitable for distributed execution with Ray.
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from requests import get, post


def extract_components(text: str, c_type: str = "hashtags") -> List[str]:
    """Extract hashtags or mentions from text using regex patterns."""
    if c_type == "hashtags":
        pattern = re.compile(r"#\w+")
    elif c_type == "mentions":
        pattern = re.compile(r"@\w+")
    else:
        return []
    
    return pattern.findall(text)


def get_user_from_post(agent_data, post_id: int) -> Dict:
    """Get the user who created a specific post."""
    api_url = f"{agent_data.base_url}/get_user_from_post"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {"post_id": post_id}
    
    response = post(api_url, headers=headers, data=json.dumps(params))
    return json.loads(response.content.decode("utf-8"))


def get_article(agent_data, post_id: int) -> Optional[Dict]:
    """Get article data associated with a post."""
    api_url = f"{agent_data.base_url}/get_article"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {"post_id": int(post_id)}
    
    response = post(api_url, headers=headers, data=json.dumps(params))
    
    if response.status_code == 404:
        return None
    
    return json.loads(response.content.decode("utf-8"))


def get_post(agent_data, post_id: int) -> Dict:
    """Get post content by ID."""
    api_url = f"{agent_data.base_url}/get_post"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {"post_id": post_id}
    
    response = post(api_url, headers=headers, data=json.dumps(params))
    return json.loads(response.content.decode("utf-8"))


def get_thread(agent_data, post_id: int, max_tweets: Optional[int] = None) -> Any:
    """Get the conversation thread for a post."""
    api_url = f"{agent_data.base_url}/post_thread"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    params = {"post_id": post_id}
    
    response = post(api_url, headers=headers, data=json.dumps(params))
    res = json.loads(response.content.decode("utf-8"))
    
    if isinstance(res, dict) and "error" in res:
        return res
    
    if max_tweets is not None and len(res) > max_tweets:
        return res[-max_tweets:]
    
    return res


def get_interests(agent_data, tid: int) -> Tuple[List[str], List[int]]:
    """Get the most recent and frequent interests of the agent."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Get current round if tid is -1
    if tid == -1:
        api_url = f"{agent_data.base_url}/current_time"
        response = get(api_url, headers=headers)
        data = json.loads(response.content.decode("utf-8"))
        tid = int(data["id"])
    
    api_url = f"{agent_data.base_url}/get_user_interests"
    data = {
        "user_id": agent_data.user_id,
        "round_id": tid,
        "n_interests": agent_data.interests if isinstance(agent_data.interests, int) else len(agent_data.interests),
        "time_window": agent_data.attention_window,
    }
    
    response = get(api_url, headers=headers, data=json.dumps(data))
    data = json.loads(response.content.decode("utf-8"))
    
    try:
        # Select random interests without replacement
        if len(data) >= 3:
            selected = np.random.choice(range(len(data)), np.random.randint(1, 3), replace=False)
        else:
            selected = np.random.choice(range(len(data)), len(data), replace=False)
        
        interests = [data[i]["topic"] for i in selected]
        interests_id = [data[i]["id"] for i in selected]
    except (IndexError, KeyError, ValueError, TypeError) as e:
        return [], []
    
    return interests, interests_id


def get_opinions(agent_data) -> Dict:
    """Get the current opinions of the agent on various topics."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/get_user_opinions"
    
    data = {"user_id": agent_data.user_id}
    response = post(api_url, headers=headers, data=json.dumps(data))
    data = json.loads(response.content.decode("utf-8"))
    
    opinions = {}
    try:
        for k, v in data.items():
            opinions[k] = v[0]
    except (IndexError, KeyError, TypeError) as e:
        return {}
    
    return opinions


def update_user_interests(agent_data, post_id: int, tid: int) -> None:
    """Update user interests based on post topics."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Get post topics
    api_url = f"{agent_data.base_url}/get_post_topics"
    data = {"post_id": post_id}
    response = get(api_url, headers=headers, data=json.dumps(data))
    data = json.loads(response.content.decode("utf-8"))
    
    if len(data) > 0:
        # Set user interests
        api_url = f"{agent_data.base_url}/set_user_interests"
        data = {"user_id": agent_data.user_id, "interests": data, "round": tid}
        post(api_url, headers=headers, data=json.dumps(data))


def follow_action(agent_data, tid: int, target: Optional[int] = None, 
                  post_id: Optional[int] = None, action: str = "follow") -> None:
    """Follow or unfollow a user."""
    if post_id is not None:
        target = get_user_from_post(agent_data, post_id)
    
    if isinstance(target, int):
        st = json.dumps({
            "user_id": agent_data.user_id,
            "target": int(target),
            "action": action,
            "tid": tid,
        })
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_url = f"{agent_data.base_url}/follow"
        post(api_url, headers=headers, data=st)


def read_posts(agent_data, article: bool = False) -> str:
    """Read posts from the content recommendation system."""
    return agent_data.content_rec_sys.read(agent_data.base_url, agent_data.user_id, article)


def read_mentions(agent_data) -> str:
    """Read mentions of the agent."""
    return agent_data.content_rec_sys.read_mentions(agent_data.base_url)


def search_posts(agent_data) -> str:
    """Search for posts using the content recommendation system."""
    return agent_data.content_rec_sys.search(agent_data.base_url)


def search_follow_suggestions(agent_data) -> Dict:
    """Get follow suggestions from the follow recommendation system."""
    return agent_data.follow_rec_sys.follow_suggestions(agent_data.base_url)


def get_followers(agent_data) -> str:
    """Get the followers of the user."""
    st = json.dumps({"user_id": agent_data.user_id})
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/followers"
    
    response = get(api_url, headers=headers, data=st)
    return response.content.decode("utf-8")


def get_timeline(agent_data) -> str:
    """Get the timeline of the user."""
    st = json.dumps({"user_id": agent_data.user_id})
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/timeline"
    
    response = get(api_url, headers=headers, data=st)
    return response.content.decode("utf-8")


def churn_system(agent_data, tid: int) -> str:
    """Mark the agent as having left the system."""
    st = json.dumps({"user_id": agent_data.user_id, "left_on": tid})
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/churn"
    
    response = post(api_url, headers=headers, data=st)
    return response.content.decode("utf-8")


def clean_text(text: str, agent_name: str) -> str:
    """Clean generated text by removing formatting artifacts."""
    text = (
        text.split("##")[-1]
        .replace("-", "")
        .replace("@ ", "")
        .replace("  ", " ")
        .replace(". ", ".")
        .replace(" ,", ",")
        .replace("[", "")
        .replace("]", "")
        .replace("@,", "")
        .strip("()[]{}'")
        .lstrip()
    )
    text = text.replace(f"@{agent_name}", "")
    return text


def clean_emotion(text: str, emotions_list: List[str]) -> List[str]:
    """Extract valid emotions from generated text."""
    try:
        emotion_eval = [
            e.strip()
            for e in text.replace("'", " ")
            .replace('"', " ")
            .replace("*", "")
            .replace(":", " ")
            .replace("[", " ")
            .replace("]", " ")
            .replace(",", " ")
            .split(" ")
            if e.strip() in emotions_list
        ]
    except:
        emotion_eval = []
    
    return emotion_eval


def effify(agent_data, non_f_str: str, **kwargs) -> str:
    """
    Convert a template string to an f-string and evaluate it.
    
    Note: This function uses eval() for template evaluation, which is necessary
    to maintain compatibility with the existing prompt system. The template strings
    are controlled by the application (not user input) via prompts.json configuration.
    """
    kwargs["self"] = agent_data
    # Only allow safe built-ins, no __builtins__
    safe_dict = {"__builtins__": {}}
    safe_dict.update(kwargs)
    return eval(f'f"""{non_f_str}"""', safe_dict)
