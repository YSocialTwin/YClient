"""
Agent LLM Functions Module - GPU-bound Operations

This module contains GPU-bound functions for agent operations that require
LLM inference. These functions operate on AgentData instances and should be
scheduled on GPU resources when using Ray for parallelization.

Functions include:
- Content generation (post, comment, share)
- Decision making (reaction, follow evaluation, action selection)
- Emotion and topic annotation
- Opinion updates with LLM evaluation

All functions are designed to be stateless and work with AgentData instances.
When using Ray, these should be marked for GPU scheduling.
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from autogen import AssistantAgent
from requests import get, post

# Import CPU-bound functions that LLM functions may need
from y_client.functions.agent_functions import (
    get_interests, get_opinions, get_post, get_thread, get_article,
    extract_components, clean_text, clean_emotion, effify, 
    update_user_interests, get_user_from_post, follow_action,
    read_posts, search_posts, search_follow_suggestions, read_mentions
)
import y_client.opinion_dynamics as op_dynamics
from y_client.opinion_dynamics.utils import get_opinion_group
from y_client.logger import log_execution_time


def emotion_annotation(agent_data, text_to_annotate: str) -> List[str]:
    """
    Annotate emotions in text using LLM.
    
    Args:
        agent_data: AgentData instance
        text_to_annotate: Text to analyze for emotions
    
    Returns:
        List of detected emotion labels
    """
    emotion_agent = AssistantAgent(
        name="EmotionAnnotator",
        llm_config=agent_data.llm_config,
        system_message=agent_data.prompts['handler_instructions'],
        max_consecutive_auto_reply=1,
    )
    
    prompt = f"Annotate the following text with the emotions it elicits:\n\n{text_to_annotate}. Answer with a JSON formatted list of emotions only."
    response = emotion_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
    
    emotion_eval = response.lower()
    emotion_eval = clean_emotion(emotion_eval, agent_data.emotions)
    
    return emotion_eval


@log_execution_time
def post_content(agent_data, tid: int) -> None:
    """
    Generate and post original content using LLM.
    
    Args:
        agent_data: AgentData instance
        tid: Time slot ID
    """
    # Get agent's current interests
    interests, interests_id = get_interests(agent_data, tid)
    
    # Build opinion and sentiment context
    agent_data.topics_opinions = "Your opinions are: "
    agent_data.topics_sentiment = "Your sentiment is: "
    
    if agent_data.opinions_enabled:
        opinions = get_opinions(agent_data)
        for interest in interests:
            if interest in opinions:
                opinions[interest] = get_opinion_group(
                    opinions[interest], 
                    agent_data.opinion_dynamics['opinion_groups']
                )
        
        for s in opinions:
            agent_data.topics_opinions += f"{s}: {opinions[s]} "
        if len(opinions) == 0:
            agent_data.topics_opinions = ""
    
    # Get sentiment on interests
    api_url = f"{agent_data.base_url}/get_sentiment"
    data = {"user_id": agent_data.user_id, "interests": interests}
    response = post(
        api_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=json.dumps(data),
    )
    sentiment = json.loads(response.content.decode("utf-8"))
    
    for s in sentiment:
        agent_data.topics_sentiment += f"{s['topic']}: {s['sentiment']} "
    
    if len(sentiment) == 0:
        agent_data.topics_sentiment = ""
    
    # Generate post using LLM
    user_agent = AssistantAgent(
        name=agent_data.name,
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["agent_roleplay"], interest=interests),
        max_consecutive_auto_reply=1,
    )
    
    prompt = effify(agent_data, agent_data.prompts["handler_post"])
    post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
    post_text = clean_text(post_text, agent_data.name)
    
    emotion_eval = []
    if agent_data.annotate_emotions:
        emotion_eval = emotion_annotation(agent_data, post_text)
    
    # Avoid posting empty messages
    if len(post_text) < 3:
        return
    
    hashtags = extract_components(post_text, c_type="hashtags")
    mentions = extract_components(post_text, c_type="mentions")
    
    st = json.dumps({
        "user_id": agent_data.user_id,
        "tweet": post_text.replace('"', ""),
        "emotions": emotion_eval,
        "hashtags": hashtags,
        "mentions": mentions,
        "tid": tid,
        "topics": interests_id,
    })
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/post"
    post(api_url, headers=headers, data=st)
    
    # Update interests
    api_url = f"{agent_data.base_url}/set_user_interests"
    data = {"user_id": agent_data.user_id, "interests": interests, "round": tid}
    post(api_url, headers=headers, data=json.dumps(data))


@log_execution_time
def comment_on_post(agent_data, post_id: int, tid: int, max_length_threads: Optional[int] = None) -> None:
    """
    Generate and post a comment on an existing post using LLM.
    
    Args:
        agent_data: AgentData instance
        post_id: ID of post to comment on
        tid: Time slot ID
        max_length_threads: Maximum thread length to read for context
    """
    conversation = get_thread(agent_data, post_id, max_tweets=max_length_threads)
    
    conv = ""
    if "error" not in conversation:
        conv = "".join(conversation)
    
    # Get post topics
    api_url = f"{agent_data.base_url}/get_post_topics_name"
    response = get(
        api_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=json.dumps({"post_id": post_id}),
    )
    interests = json.loads(response.content.decode("utf-8"))
    
    agent_data.topics_opinions = "Your opinions on the discussion topics are: "
    agent_data.topics_sentiment = "Your sentiment on the discussion topics are: "
    
    if agent_data.opinions_enabled:
        opinions = get_opinions(agent_data)
        for interest in interests:
            if interest in opinions:
                opinions[interest] = get_opinion_group(
                    opinions[interest],
                    agent_data.opinion_dynamics['opinion_groups']
                )
        
        for s in opinions:
            agent_data.topics_opinions += f"{s}: {opinions[s]}\n "
        if len(opinions) == 0:
            agent_data.topics_opinions = ""
    
    # Get sentiment
    if len(interests) > 0:
        api_url = f"{agent_data.base_url}/get_sentiment"
        data = {"user_id": agent_data.user_id, "interests": interests}
        response = post(
            api_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        sentiment = json.loads(response.content.decode("utf-8"))
        
        for s in sentiment:
            agent_data.topics_sentiment += f"{s['topic']}: {s['sentiment']} "
        if len(sentiment) == 0:
            agent_data.topics_sentiment = ""
    
    # Generate comment using LLM
    user_agent = AssistantAgent(
        name=agent_data.name,
        llm_config=agent_data.llm_config,
        system_message=effify(
            agent_data, 
            agent_data.prompts["agent_roleplay_comments_share"], 
            interest=interests
        ),
        max_consecutive_auto_reply=1,
    )
    
    prompt = effify(agent_data, agent_data.prompts["handler_comment"], conv=conv)
    post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
    post_text = clean_text(post_text, agent_data.name)
    
    emotion_eval = []
    if agent_data.annotate_emotions:
        emotion_eval = emotion_annotation(agent_data, post_text)
    
    # Avoid posting empty messages
    if len(post_text) < 3:
        return
    
    hashtags = extract_components(post_text, c_type="hashtags")
    mentions = extract_components(post_text, c_type="mentions")
    
    st = json.dumps({
        "user_id": agent_data.user_id,
        "post_id": post_id,
        "text": post_text.replace('"', "").replace(f"{agent_data.name}", "").replace(":", "").replace("*", ""),
        "emotions": emotion_eval,
        "hashtags": hashtags,
        "mentions": mentions,
        "tid": tid,
    })
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/comment"
    post(api_url, headers=headers, data=st)
    
    # Update interests and handle follow/unfollow
    api_url = f"{agent_data.base_url}/get_thread_root"
    response = get(api_url, headers=headers, data=json.dumps({"post_id": post_id}))
    data = json.loads(response.content.decode("utf-8"))
    update_user_interests(agent_data, data, tid)
    
    # Update opinions if enabled
    if agent_data.opinions_enabled:
        update_opinions(agent_data, post_id, tid, post_text)


@log_execution_time
def share_post(agent_data, post_id: int, tid: int) -> None:
    """
    Share a post with commentary generated by LLM.
    
    Args:
        agent_data: AgentData instance
        post_id: ID of post to share
        tid: Time slot ID
    """
    article = get_article(agent_data, post_id)
    if article is not None and "status" in article:
        return
    
    post_text = get_post(agent_data, post_id)
    
    # Get post topics
    api_url = f"{agent_data.base_url}/get_post_topics_name"
    response = get(
        api_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=json.dumps({"post_id": post_id}),
    )
    interests = json.loads(response.content.decode("utf-8"))
    
    agent_data.topics_opinions = ""
    if len(interests) > 0:
        api_url = f"{agent_data.base_url}/get_sentiment"
        data = {"user_id": agent_data.user_id, "interests": interests}
        response = post(
            api_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=json.dumps(data),
        )
        sentiment = json.loads(response.content.decode("utf-8"))
        
        agent_data.topics_opinions = "Your opinion topics of the post you are responding to are: "
        for s in sentiment:
            agent_data.topics_opinions += f"{s['topic']}: {s['sentiment']} "
        if len(sentiment) == 0:
            agent_data.topics_opinions = ""
    else:
        interests, _ = get_interests(agent_data, tid)
    
    # Generate share commentary using LLM
    user_agent = AssistantAgent(
        name=agent_data.name,
        llm_config=agent_data.llm_config,
        system_message=effify(
            agent_data,
            agent_data.prompts["agent_roleplay_comments_share"],
            interest=interests
        ),
        max_consecutive_auto_reply=1,
    )
    
    prompt = effify(agent_data, agent_data.prompts["handler_share"], article=article, post_text=post_text)
    post_text = user_agent.generate_reply(messages=[{"role": "user", "content": prompt}])
    post_text = (
        post_text.split(":")[-1]
        .split("-")[-1]
        .replace("@ ", "")
        .replace("  ", " ")
        .replace(". ", ".")
        .replace(" ,", ",")
        .replace("[", "")
        .replace("]", "")
        .replace("@,", "")
    )
    post_text = post_text.replace(f"@{agent_data.name}", "")
    
    emotion_eval = []
    if agent_data.annotate_emotions:
        emotion_eval = emotion_annotation(agent_data, post_text)
    
    hashtags = extract_components(post_text, c_type="hashtags")
    mentions = extract_components(post_text, c_type="mentions")
    
    st = json.dumps({
        "user_id": agent_data.user_id,
        "post_id": post_id,
        "text": post_text.replace('"', ""),
        "emotions": emotion_eval,
        "hashtags": hashtags,
        "mentions": mentions,
        "tid": tid,
    })
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/share"
    post(api_url, headers=headers, data=st)


@log_execution_time
def reaction_to_post(agent_data, post_id: int, tid: int, check_follow: bool = True) -> None:
    """
    Generate a like/dislike reaction to a post using LLM decision.
    
    Args:
        agent_data: AgentData instance
        post_id: ID of post to react to
        tid: Time slot ID
        check_follow: Whether to evaluate follow action
    """
    post_text = get_post(agent_data, post_id)
    
    u1 = AssistantAgent(
        name=f"{agent_data.name}",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["agent_roleplay_simple"]),
        max_consecutive_auto_reply=1,
    )
    
    u2 = AssistantAgent(
        name=f"Handler",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["handler_instructions_simple"]),
        max_consecutive_auto_reply=0,
    )
    
    u2.initiate_chat(
        u1,
        message=effify(agent_data, agent_data.prompts["handler_reactions"], post_text=post_text),
        silent=True,
        max_round=1,
    )
    
    text = u1.chat_messages[u2][-1]["content"].replace("!", "")
    
    u1.reset()
    u2.reset()
    
    if "YES" in text.split():
        st = json.dumps({
            "user_id": agent_data.user_id,
            "post_id": post_id,
            "type": "like",
            "tid": tid,
        })
        flag = "follow"
    elif "NO" in text.split():
        st = json.dumps({
            "user_id": agent_data.user_id,
            "post_id": post_id,
            "type": "dislike",
            "tid": tid,
        })
        flag = "unfollow"
        if agent_data.probability_of_secondary_follow > 0:
            evaluate_follow(agent_data, post_text, post_id, flag, tid)
    else:
        return
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/reaction"
    post(api_url, headers=headers, data=st)
    
    if agent_data.probability_of_secondary_follow > 0:
        if check_follow and flag == "follow":
            evaluate_follow(agent_data, post_text, post_id, flag, tid)
    
    update_user_interests(agent_data, post_id, tid)


def evaluate_follow(agent_data, post_text: str, post_id: int, action: str, tid: int) -> Optional[str]:
    """
    Use LLM to decide whether to follow/unfollow based on post content.
    
    Args:
        agent_data: AgentData instance
        post_text: Content of the post
        post_id: ID of the post
        action: "follow" or "unfollow"
        tid: Time slot ID
    
    Returns:
        Action taken or None
    """
    if agent_data.probability_of_secondary_follow > 0:
        if np.random.rand() > agent_data.probability_of_secondary_follow:
            return None
    else:
        return None
    
    u1 = AssistantAgent(
        name=f"{agent_data.name}",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["agent_roleplay_simple"]),
        max_consecutive_auto_reply=1,
    )
    
    u2 = AssistantAgent(
        name=f"Handler",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["handler_instructions_simple"]),
        max_consecutive_auto_reply=0,
    )
    
    u2.initiate_chat(
        u1,
        message=effify(agent_data, agent_data.prompts["handler_follow"], post_text=post_text, action=action),
        silent=True,
        max_round=1,
    )
    
    text = u1.chat_messages[u2][-1]["content"].replace("!", "")
    
    u1.reset()
    u2.reset()
    
    if "YES" in text.split():
        follow_action(agent_data, tid=tid, post_id=post_id, action=action)
        return action
    else:
        return None


@log_execution_time
def cast_vote(agent_data, post_id: int, tid: int) -> None:
    """
    Cast a political vote using LLM decision.
    
    Args:
        agent_data: AgentData instance
        post_id: ID of post to vote on
        tid: Time slot ID
    """
    post_text = get_post(agent_data, post_id)
    
    u1 = AssistantAgent(
        name=f"{agent_data.name}",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["agent_roleplay_simple"]),
        max_consecutive_auto_reply=1,
    )
    
    u2 = AssistantAgent(
        name=f"Handler",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["handler_instructions_simple"]),
        max_consecutive_auto_reply=0,
    )
    
    u2.initiate_chat(
        u1,
        message=effify(agent_data, agent_data.prompts["handler_cast"], post_text=post_text),
        silent=True,
        max_round=1,
    )
    
    text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()
    
    u1.reset()
    u2.reset()
    
    data = {
        "user_id": agent_data.user_id,
        "post_id": post_id,
        "content_type": "Post",
        "tid": tid,
        "content_id": post_id,
    }
    
    if "RIGHT" in text.split():
        data["vote"] = "R"
    elif "LEFT" in text.split():
        data["vote"] = "D"
    elif "NONE" in text.split():
        data["vote"] = "U"
    else:
        return
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    api_url = f"{agent_data.base_url}/cast_preference"
    post(api_url, headers=headers, data=json.dumps(data))


def update_opinions(agent_data, post_id: int, tid: int, text: str) -> bool:
    """
    Update agent opinions based on interaction with a post.
    
    Args:
        agent_data: AgentData instance
        post_id: ID of post interacted with
        tid: Time slot ID
        text: Content of the interaction
    
    Returns:
        True if successful
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Get post topics
    api_url = f"{agent_data.base_url}/get_post_topics"
    response = get(api_url, headers=headers, data=json.dumps({"post_id": post_id}))
    interests = json.loads(response.content.decode("utf-8"))
    
    # Get author
    api_url = f"{agent_data.base_url}/get_post_author"
    response = get(api_url, headers=headers, data=json.dumps({"post_id": post_id}))
    author_data = json.loads(response.content.decode("utf-8"))
    author_id = author_data.get("user_id", None)
    
    # Get author opinions
    api_url = f"{agent_data.base_url}/get_user_opinions"
    data = {"user_id": author_id}
    response = post(api_url, headers=headers, data=json.dumps(data))
    opinions = json.loads(response.content.decode("utf-8"))
    
    filtered_opinions = {
        v[1]: v[0]
        for t, v in opinions.items()
        if int(v[1]) in interests
    }
    
    # Get agent opinions
    api_url = f"{agent_data.base_url}/get_user_opinions"
    data = {"user_id": agent_data.user_id}
    response = post(api_url, headers=headers, data=json.dumps(data))
    agent_opinions = json.loads(response.content.decode("utf-8"))
    
    agent_filtered_opinions = {
        v[1]: v[0]
        for t, v in agent_opinions.items()
        if int(v[1]) in interests
    }
    
    filtered_topics = {
        v[1]: t
        for t, v in agent_opinions.items()
        if int(v[1]) in interests
    }
    
    method_name = agent_data.opinion_dynamics['model_name']
    update = getattr(op_dynamics, method_name)
    
    for topic, opinion in filtered_opinions.items():
        if topic in agent_filtered_opinions:
            tp_name = filtered_topics[topic]
            
            agent_filtered_opinions[topic] = update(
                uid=agent_data.user_id,
                x=agent_filtered_opinions[topic],
                y=opinion,
                text=text,
                topic=tp_name,
                **agent_data.opinion_dynamics['parameters'],
                group_classes=agent_data.opinion_dynamics['opinion_groups'],
                base_url=agent_data.base_url,
                llm_config=agent_data.llm_config
            )
    
    # Set new opinions
    api_url = f"{agent_data.base_url}/set_user_opinions"
    data = {
        "user_id": agent_data.user_id,
        "opinions": agent_filtered_opinions,
        "id_post": int(post_id),
        "id_interacted_with": int(author_id),
        "round": int(tid),
    }
    
    post(api_url, headers=headers, data=json.dumps(data))
    
    return True


@log_execution_time
def select_action_llm(agent_data, tid: int, actions: List[str], max_length_thread_reading: int = 5) -> None:
    """
    Use LLM to select and execute an action from available options.
    
    Args:
        agent_data: AgentData instance
        tid: Time slot ID
        actions: List of possible actions
        max_length_thread_reading: Max thread length for comments
    """
    np.random.shuffle(actions)
    acts = ",".join(actions)
    
    u1 = AssistantAgent(
        name=f"{agent_data.name}",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["agent_roleplay_base"]),
        max_consecutive_auto_reply=1,
    )
    
    u2 = AssistantAgent(
        name=f"Handler",
        llm_config=agent_data.llm_config,
        system_message=effify(agent_data, agent_data.prompts["handler_instructions_simple"]),
        max_consecutive_auto_reply=0,
    )
    
    u2.initiate_chat(
        u1,
        message=effify(agent_data, agent_data.prompts["handler_action"], actions=acts),
        silent=True,
        max_round=1,
    )
    
    text = u1.chat_messages[u2][-1]["content"].replace("!", "").upper()
    u1.reset()
    u2.reset()
    
    if "COMMENT" in text.split():
        candidates = json.loads(read_posts(agent_data))
        if len(candidates) > 0:
            selected_post = random.sample(candidates, 1)
            comment_on_post(agent_data, int(selected_post[0]), tid, max_length_threads=max_length_thread_reading)
            reaction_to_post(agent_data, int(selected_post[0]), tid, check_follow=False)
    
    elif "POST" in text.split():
        post_content(agent_data, tid=tid)
    
    elif "READ" in text.split():
        candidates = json.loads(read_posts(agent_data))
        try:
            selected_post = random.sample(candidates, 1)
            reaction_to_post(agent_data, int(selected_post[0]), tid)
        except (IndexError, ValueError, KeyError, TypeError):
            pass
    
    elif "SEARCH" in text.split():
        candidates = json.loads(search_posts(agent_data))
        if "status" not in candidates and len(candidates) > 0:
            selected_post = random.sample(candidates, 1)
            comment_on_post(agent_data, int(selected_post[0]), tid, max_length_threads=max_length_thread_reading)
            reaction_to_post(agent_data, int(selected_post[0]), tid, check_follow=False)
    
    elif "FOLLOW" in text.split():
        if agent_data.probability_of_daily_follow > 0:
            candidates = search_follow_suggestions(agent_data)
            if len(candidates) > 0:
                tot = sum([float(v) for v in candidates.values()])
                probs = [v / tot for v in candidates.values()]
                selected = np.random.choice(
                    [int(c) for c in candidates],
                    p=probs,
                    size=1,
                )[0]
                follow_action(agent_data, tid=tid, target=selected, action="follow")
    
    elif "SHARE" in text.split():
        candidates = json.loads(read_posts(agent_data, article=True))
        if len(candidates) > 0:
            selected_post = random.sample(candidates, 1)
            share_post(agent_data, int(selected_post[0]), tid)
    
    elif "CAST" in text.split():
        candidates = json.loads(read_posts(agent_data))
        try:
            selected_post = random.sample(candidates, 1)
            cast_vote(agent_data, int(selected_post[0]), tid)
        except (IndexError, ValueError, KeyError, TypeError):
            pass
