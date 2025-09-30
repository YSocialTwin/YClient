#!/usr/bin/env python3
"""
Comprehensive unit tests for y_client/classes/annotator.py module.

This module tests the Annotator class for image annotation functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from y_client.classes.annotator import Annotator


class TestAnnotator(unittest.TestCase):
    """Test class for y_client.classes.annotator.Annotator."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = {
            "model": "test-model",
            "url": "http://localhost:8080",
            "api_key": "test-api-key",
            "temperature": 0.7,
            "max_tokens": 500
        }

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_init_basic(self, mock_assistant_agent, mock_multimodal_agent):
        """Test basic initialization of Annotator."""
        # Create mocks
        mock_image_agent = MagicMock()
        mock_user_proxy = MagicMock()
        mock_multimodal_agent.return_value = mock_image_agent
        mock_assistant_agent.return_value = mock_user_proxy
        
        # Create Annotator instance
        annotator = Annotator(self.mock_config)
        
        # Verify initialization
        self.assertEqual(len(annotator.config_list), 1)
        config = annotator.config_list[0]
        self.assertEqual(config["model"], "test-model")
        self.assertEqual(config["base_url"], "http://localhost:8080")
        self.assertEqual(config["api_key"], "test-api-key")
        self.assertEqual(config["timeout"], 10000)
        self.assertEqual(config["api_type"], "open_ai")
        self.assertEqual(config["price"], [0, 0])
        
        # Verify agents were created correctly
        mock_multimodal_agent.assert_called_once_with(
            name="image-explainer",
            max_consecutive_auto_reply=1,
            llm_config={
                "config_list": annotator.config_list,
                "temperature": 0.7,
                "max_tokens": 500,
            },
            human_input_mode="NEVER",
        )
        
        mock_assistant_agent.assert_called_once_with(
            name="User_proxy",
            max_consecutive_auto_reply=0,
        )
        
        # Verify agents are stored correctly
        self.assertEqual(annotator.image_agent, mock_image_agent)
        self.assertEqual(annotator.user_proxy, mock_user_proxy)

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_annotate_success(self, mock_assistant_agent, mock_multimodal_agent):
        """Test successful image annotation."""
        # Setup mocks
        mock_image_agent = MagicMock()
        mock_user_proxy = MagicMock()
        mock_multimodal_agent.return_value = mock_image_agent
        mock_assistant_agent.return_value = mock_user_proxy
        
        # Mock chat_messages structure
        mock_response_content = "This is a test image showing a cat sitting on a chair."
        mock_image_agent.chat_messages = {
            mock_user_proxy: [
                {
                    "content": [
                        {"text": mock_response_content}
                    ]
                }
            ]
        }
        
        # Create Annotator and test annotation
        annotator = Annotator(self.mock_config)
        test_image = "http://example.com/test_image.jpg"
        result = annotator.annotate(test_image)
        
        # Verify initiate_chat was called correctly
        mock_user_proxy.initiate_chat.assert_called_once_with(
            mock_image_agent,
            silent=True,
            message=f"""Describe the following image. 
            Write in english. <img {test_image}>""",
        )
        
        # Verify result
        self.assertEqual(result, mock_response_content)

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_annotate_failure_response(self, mock_assistant_agent, mock_multimodal_agent):
        """Test annotation when the model returns an 'I'm sorry' response."""
        # Setup mocks
        mock_image_agent = MagicMock()
        mock_user_proxy = MagicMock()
        mock_multimodal_agent.return_value = mock_image_agent
        mock_assistant_agent.return_value = mock_user_proxy
        
        # Mock chat_messages with failure response
        mock_failure_response = "I'm sorry, I cannot analyze this image."
        mock_image_agent.chat_messages = {
            mock_user_proxy: [
                {
                    "content": [
                        {"text": mock_failure_response}
                    ]
                }
            ]
        }
        
        # Create Annotator and test annotation
        annotator = Annotator(self.mock_config)
        test_image = "http://example.com/broken_image.jpg"
        result = annotator.annotate(test_image)
        
        # Verify initiate_chat was called
        mock_user_proxy.initiate_chat.assert_called_once()
        
        # Verify result is None for failure cases
        self.assertIsNone(result)

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_annotate_empty_response(self, mock_assistant_agent, mock_multimodal_agent):
        """Test annotation when the response is empty or malformed."""
        # Setup mocks
        mock_image_agent = MagicMock()
        mock_user_proxy = MagicMock()
        mock_multimodal_agent.return_value = mock_image_agent
        mock_assistant_agent.return_value = mock_user_proxy
        
        # Mock empty chat_messages
        mock_image_agent.chat_messages = {
            mock_user_proxy: []
        }
        
        # Create Annotator and test annotation
        annotator = Annotator(self.mock_config)
        test_image = "http://example.com/test_image.jpg"
        
        # Should raise IndexError when trying to access [-1] on empty list
        with self.assertRaises(IndexError):
            annotator.annotate(test_image)

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_annotate_with_different_image_urls(self, mock_assistant_agent, mock_multimodal_agent):
        """Test annotation with different types of image URLs."""
        # Setup mocks
        mock_image_agent = MagicMock()
        mock_user_proxy = MagicMock()
        mock_multimodal_agent.return_value = mock_image_agent
        mock_assistant_agent.return_value = mock_user_proxy
        
        # Mock successful response
        mock_response_content = "This is an image."
        mock_image_agent.chat_messages = {
            mock_user_proxy: [
                {
                    "content": [
                        {"text": mock_response_content}
                    ]
                }
            ]
        }
        
        annotator = Annotator(self.mock_config)
        
        # Test with various image URL formats
        test_images = [
            "https://example.com/image.jpg",
            "http://localhost/test.png",
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/",
            "file:///path/to/image.gif"
        ]
        
        for image_url in test_images:
            # Reset mock for each test
            mock_user_proxy.reset_mock()
            
            result = annotator.annotate(image_url)
            
            # Verify call was made with correct image URL
            mock_user_proxy.initiate_chat.assert_called_with(
                mock_image_agent,
                silent=True,
                message=f"""Describe the following image. 
            Write in english. <img {image_url}>""",
            )
            
            self.assertEqual(result, mock_response_content)

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_config_list_structure(self, mock_assistant_agent, mock_multimodal_agent):
        """Test that config_list is structured correctly."""
        # Create Annotator instance
        annotator = Annotator(self.mock_config)
        
        # Verify config_list structure
        self.assertIsInstance(annotator.config_list, list)
        self.assertEqual(len(annotator.config_list), 1)
        
        config = annotator.config_list[0]
        required_keys = ["model", "base_url", "timeout", "api_type", "api_key", "price"]
        
        for key in required_keys:
            self.assertIn(key, config)
        
        # Verify specific values
        self.assertEqual(config["timeout"], 10000)
        self.assertEqual(config["api_type"], "open_ai")
        self.assertEqual(config["price"], [0, 0])

    @patch('y_client.classes.annotator.MultimodalConversableAgent')
    @patch('y_client.classes.annotator.autogen.AssistantAgent')
    def test_missing_config_values(self, mock_assistant_agent, mock_multimodal_agent):
        """Test behavior with missing configuration values."""
        # Test with minimal config
        minimal_config = {
            "model": "test-model",
            "url": "http://localhost:8080",
            "api_key": "test-key"
        }
        
        # Should raise KeyError for missing temperature or max_tokens
        with self.assertRaises(KeyError):
            Annotator(minimal_config)

    def test_annotator_class_structure(self):
        """Test Annotator class structure and methods."""
        # Test that the class exists and has the expected module
        self.assertEqual(Annotator.__module__, 'y_client.classes.annotator')
        
        # Test that the class is properly defined
        self.assertTrue(hasattr(Annotator, '__init__'))
        self.assertTrue(hasattr(Annotator, 'annotate'))
        
        # Test that the class has the expected docstring or attributes
        self.assertTrue(callable(Annotator))


if __name__ == '__main__':
    unittest.main()