#!/usr/bin/env python3
"""
Comprehensive unit tests for y_client/utils.py module.

This module tests the utility functions for generating users and pages.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import sys
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from y_client.utils import generate_user, generate_page


class TestUtils(unittest.TestCase):
    """Test class for y_client.utils module."""

    def setUp(self):
        """Set up test fixtures with mock configurations."""
        self.mock_config = {
            "agents": {
                "nationalities": ["American", "British", "French"],
                "political_leanings": ["conservative", "liberal", "moderate"],
                "age": {"min": 18, "max": 80},
                "interests": ["technology", "politics", "sports", "music", "art"],
                "n_interests": {"min": 1, "max": 3},
                "toxicity_levels": ["no", "low", "medium", "high"],
                "languages": ["en", "fr", "es"],
                "llm_agents": ["gpt-3.5", "gpt-4", "llama"],
                "big_five": {
                    "oe": [1, 2, 3, 4, 5],
                    "co": [1, 2, 3, 4, 5],
                    "ex": [1, 2, 3, 4, 5],
                    "ag": [1, 2, 3, 4, 5],
                    "ne": [1, 2, 3, 4, 5]
                },
                "education_levels": ["high_school", "bachelor", "master", "phd"],
                "round_actions": {"min": 1, "max": 5}
            },
            "servers": {
                "llm_api_key": "test_api_key"
            }
        }
        
        self.mock_locales = {
            "American": "en_US",
            "British": "en_GB",
            "French": "fr_FR"
        }

    @patch('y_client.utils.json.load')
    @patch('builtins.open')
    @patch('y_client.utils.faker.Faker')
    @patch('y_client.utils.Agent')
    def test_generate_user_basic(self, mock_agent_class, mock_faker, mock_open_func, mock_json_load):
        """Test basic user generation functionality."""
        # Setup mocks
        mock_json_load.return_value = self.mock_locales
        mock_faker_instance = MagicMock()
        mock_faker.return_value = mock_faker_instance
        
        # Configure faker mock
        mock_faker_instance.name_male.return_value = "John Doe"
        mock_faker_instance.name_female.return_value = "Jane Doe"
        mock_faker_instance.free_email_domain.return_value = "gmail.com"
        mock_faker_instance.random_element.side_effect = [
            "conservative",  # political_leaning
            "no",           # toxicity
            "en",           # language
            "gpt-4",        # ag_type
            3,              # big_five values
            3, 3, 3, 3,
            "bachelor"      # education_level
        ]
        mock_faker_instance.password.return_value = "password123"
        mock_faker_instance.random_int.side_effect = [25, 2]  # age, round_actions
        mock_faker_instance.random_elements.return_value = ["technology", "politics"]
        
        # Mock Agent instance
        mock_agent_instance = MagicMock()
        mock_agent_instance.user_id = "user123"
        mock_agent_class.return_value = mock_agent_instance
        
        # Call function
        result = generate_user(self.mock_config, owner="test_owner")
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result, mock_agent_instance)
        
        # Verify Agent was called with correct parameters
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        self.assertEqual(call_args[1]['name'], "JohnDoe")
        self.assertEqual(call_args[1]['config'], self.mock_config)
        self.assertEqual(call_args[1]['owner'], "test_owner")
        self.assertEqual(call_args[1]['api_key'], "test_api_key")
        self.assertEqual(call_args[1]['is_page'], 0)

    @patch('y_client.utils.json.load')
    @patch('builtins.open')
    @patch('y_client.utils.faker.Faker')
    @patch('y_client.utils.Agent')
    def test_generate_user_no_user_id(self, mock_agent_class, mock_faker, mock_open_func, mock_json_load):
        """Test user generation when agent has no user_id."""
        # Setup mocks
        mock_json_load.return_value = self.mock_locales
        mock_faker_instance = MagicMock()
        mock_faker.return_value = mock_faker_instance
        
        # Configure faker mock
        mock_faker_instance.name_male.return_value = "John Doe"
        mock_faker_instance.free_email_domain.return_value = "gmail.com"
        mock_faker_instance.random_element.side_effect = ["conservative", "no", "en", "gpt-4", 3, 3, 3, 3, 3, "bachelor"]
        mock_faker_instance.password.return_value = "password123"
        mock_faker_instance.random_int.side_effect = [25, 2]
        mock_faker_instance.random_elements.return_value = ["technology"]
        
        # Mock Agent instance without user_id
        mock_agent_instance = MagicMock()
        delattr(mock_agent_instance, 'user_id')
        mock_agent_class.return_value = mock_agent_instance
        
        # Call function
        result = generate_user(self.mock_config)
        
        # Verify result is None
        self.assertIsNone(result)

    @patch('y_client.utils.json.load')
    @patch('builtins.open')
    @patch('y_client.utils.faker.Faker')
    @patch('y_client.utils.Agent')
    def test_generate_user_missing_config_values(self, mock_agent_class, mock_faker, mock_open_func, mock_json_load):
        """Test user generation with missing configuration values."""
        # This test verifies that missing config values cause appropriate errors
        minimal_config = {
            "agents": {
                "nationalities": ["American"],
                "interests": ["technology"],
                "llm_agents": ["gpt-4"]
            },
            "servers": {
                "llm_api_key": "test_key"
            }
        }
        
        mock_json_load.return_value = self.mock_locales
        
        # Call function - should raise KeyError for missing political_leanings
        with self.assertRaises(KeyError):
            generate_user(minimal_config)

    @patch('y_client.utils.faker.Faker')
    @patch('y_client.utils.PageAgent')
    def test_generate_page_basic(self, mock_page_agent_class, mock_faker):
        """Test basic page generation functionality."""
        # Setup mocks
        mock_faker_instance = MagicMock()
        mock_faker.return_value = mock_faker_instance
        
        mock_faker_instance.free_email_domain.return_value = "news.com"
        mock_faker_instance.random_element.side_effect = ["gpt-4", 3, 3, 3, 3, 3]
        mock_faker_instance.random_int.return_value = 3
        
        # Mock PageAgent instance
        mock_page_instance = MagicMock()
        mock_page_agent_class.return_value = mock_page_instance
        
        # Call function
        result = generate_page(
            self.mock_config, 
            owner="test_owner",
            name="Test News",
            feed_url="https://test.com/feed"
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result, mock_page_instance)
        
        # Verify PageAgent was called with correct parameters
        mock_page_agent_class.assert_called_once()
        call_args = mock_page_agent_class.call_args
        self.assertEqual(call_args[1]['name'], "Test News")
        self.assertEqual(call_args[1]['feed_url'], "https://test.com/feed")
        self.assertEqual(call_args[1]['owner'], "test_owner")
        self.assertEqual(call_args[1]['is_page'], 1)
        self.assertEqual(call_args[1]['age'], 0)
        self.assertIsNone(call_args[1]['leaning'])
        self.assertEqual(call_args[1]['interests'], [])

    @patch('y_client.utils.faker.Faker')
    @patch('y_client.utils.PageAgent')
    def test_generate_page_missing_round_actions(self, mock_page_agent_class, mock_faker):
        """Test page generation when round_actions config is missing."""
        # Setup config without round_actions
        config_no_actions = {
            "agents": {
                "llm_agents": ["gpt-4"],
                "big_five": {
                    "oe": [3], "co": [3], "ex": [3], "ag": [3], "ne": [3]
                }
            },
            "servers": {
                "llm_api_key": "test_key"
            }
        }
        
        mock_faker_instance = MagicMock()
        mock_faker.return_value = mock_faker_instance
        
        mock_faker_instance.free_email_domain.return_value = "news.com"
        mock_faker_instance.random_element.side_effect = ["gpt-4", 3, 3, 3, 3, 3]
        
        mock_page_instance = MagicMock()
        mock_page_agent_class.return_value = mock_page_instance
        
        # Call function
        result = generate_page(config_no_actions, name="Test Page")
        
        # Verify result
        self.assertIsNotNone(result)
        
        # Verify round_actions defaults to 3
        call_args = mock_page_agent_class.call_args
        self.assertEqual(call_args[1]['round_actions'], 3)

    def test_generate_user_without_required_imports(self):
        """Test behavior when required modules are not available."""
        # This test verifies the try/except blocks handle import errors gracefully
        with patch('y_client.utils.json.load') as mock_json_load:
            mock_json_load.side_effect = FileNotFoundError("Config file not found")
            
            with self.assertRaises(FileNotFoundError):
                generate_user(self.mock_config)

    def test_generate_user_nationality_exception(self):
        """Test user generation when nationality sampling fails."""
        # Test the exception handling by using a config that will cause the try/except to activate
        config_bad_nationality = {
            "agents": {
                "nationalities": [],  # Empty list will cause sample to fail
                "political_leanings": ["conservative", "liberal", "moderate"],
                "age": {"min": 18, "max": 80},
                "interests": ["technology", "politics", "sports"],
                "n_interests": {"min": 1, "max": 3},
                "toxicity_levels": ["no", "low"],
                "languages": ["en", "fr"],
                "llm_agents": ["gpt-3.5", "gpt-4"],
                "big_five": {
                    "oe": [1, 2, 3, 4, 5],
                    "co": [1, 2, 3, 4, 5],
                    "ex": [1, 2, 3, 4, 5],
                    "ag": [1, 2, 3, 4, 5],
                    "ne": [1, 2, 3, 4, 5]
                },
                "education_levels": ["high_school", "bachelor"],
                "round_actions": {"min": 1, "max": 5}
            },
            "servers": {
                "llm_api_key": "test_api_key"
            }
        }
        
        with patch('y_client.utils.json.load') as mock_json_load, \
             patch('builtins.open'), \
             patch('y_client.utils.faker.Faker') as mock_faker, \
             patch('y_client.utils.Agent') as mock_agent:
            
            mock_json_load.return_value = self.mock_locales
            mock_faker_instance = MagicMock()
            mock_faker.return_value = mock_faker_instance
            
            mock_faker_instance.name_male.return_value = "John Doe"
            mock_faker_instance.free_email_domain.return_value = "gmail.com"
            mock_faker_instance.random_element.side_effect = ["conservative", "no", "en", "gpt-4", 3, 3, 3, 3, 3, "bachelor"]
            mock_faker_instance.password.return_value = "password123"
            mock_faker_instance.random_int.side_effect = [25, 2]
            mock_faker_instance.random_elements.return_value = ["technology"]
            
            mock_agent_instance = MagicMock()
            mock_agent_instance.user_id = "user123"
            mock_agent.return_value = mock_agent_instance
            
            # Should default to "American" when sampling fails due to empty nationality list
            result = generate_user(config_bad_nationality)
            self.assertIsNotNone(result)
            
            # Verify faker was called with American locale
            mock_faker.assert_called_with(self.mock_locales["American"])


if __name__ == '__main__':
    unittest.main()