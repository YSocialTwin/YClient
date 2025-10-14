"""
Annotator Module

This module provides image annotation capabilities using multimodal LLM agents.
It can analyze and describe images shared in the social network simulation.
"""

import autogen
from autogen.agentchat.contrib.multimodal_conversable_agent import (
    MultimodalConversableAgent,
)


class Annotator(object):
    """
    Image annotator using multimodal LLM for generating image descriptions.
    
    This class wraps a multimodal conversable agent that can analyze images
    and provide textual descriptions. It's used to process images shared
    in posts within the social network simulation.
    
    Attributes:
        config_list (list): Configuration for the LLM model
        image_agent (MultimodalConversableAgent): Agent for image analysis
        user_proxy (AssistantAgent): Proxy agent for managing conversations
    """
    
    def __init__(self, config):
        """
        Initialize the Annotator with LLM configuration.
        
        Args:
            config (dict): Configuration dictionary containing:
                - model (str): Name of the LLM model to use
                - url (str): Base URL for the LLM API
                - api_key (str): API key for authentication
                - temperature (float): Temperature for response generation
                - max_tokens (int): Maximum tokens for response
        """
        self.config_list = [
            {
                "model": config["model"],
                "base_url": config["url"],
                "timeout": 10000,
                "api_type": "open_ai",
                "api_key": config["api_key"],
                "price": [0, 0],
            }
        ]

        self.image_agent = MultimodalConversableAgent(
            name="image-explainer",
            max_consecutive_auto_reply=1,
            llm_config={
                "config_list": self.config_list,
                "temperature": config["temperature"],
                "max_tokens": config["max_tokens"],
            },
            human_input_mode="NEVER",
        )

        self.user_proxy = autogen.AssistantAgent(
            name="User_proxy",
            max_consecutive_auto_reply=0,
        )

    def annotate(self, image):
        """
        Generate a textual description of an image.
        
        This method uses the multimodal LLM to analyze an image and produce
        a description in English. If the model cannot process the image or
        returns an error response, None is returned.
        
        Args:
            image (str): URL or path to the image to annotate
            
        Returns:
            str or None: Text description of the image, or None if annotation fails
                        or the model returns an error message
        """
        self.user_proxy.initiate_chat(
            self.image_agent,
            silent=True,
            message=f"""Describe the following image. 
            Write in english. <img {image}>""",
        )

        res = self.image_agent.chat_messages[self.user_proxy][-1]["content"][-1]["text"]
        if "I'm sorry" in res:
            res = None
        return res
