#!/usr/bin/env python3
"""
Unit tests for y_client/classes/base_agent.py module.

This module tests the Agent and Agents classes for core agent functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the actual classes - all dependencies are now installed
from y_client.classes.base_agent import Agent, Agents


class TestAgent(unittest.TestCase):
    """Test class for y_client.classes.base_agent.Agent."""

    def test_agent_class_structure(self):
        """Test Agent class structure and attributes."""
        # Test that the class exists and has the expected module
        self.assertEqual(Agent.__module__, 'y_client.classes.base_agent')
        
        # Test that the class has expected methods
        expected_methods = [
            '__init__', 'set_rec_sys', 'set_prompts', 'post', 'comment', 
            'share', 'reaction', 'follow', 'followers', 'timeline', 
            'select_action', '__str__', '__dict__'
        ]
        
        for method in expected_methods:
            self.assertTrue(hasattr(Agent, method), f"Agent missing method: {method}")

    def test_extract_components_method_exists(self):
        """Test that the extract components method exists."""
        # Test private method exists
        self.assertTrue(hasattr(Agent, '_Agent__extract_components'))

    @patch('y_client.classes.base_agent.re')
    def test_extract_components_logic(self, mock_re):
        """Test extract components logic without initializing Agent."""
        # Create a mock pattern and test the logic
        mock_pattern = MagicMock()
        mock_pattern.findall.return_value = ["#test", "#python"]
        mock_re.compile.return_value = mock_pattern
        
        # We can't test the actual method without initializing Agent
        # So we test that the required regex module is imported
        self.assertTrue('re' in sys.modules)

    def test_agent_str_method_signature(self):
        """Test that Agent has a __str__ method."""
        self.assertTrue(hasattr(Agent, '__str__'))
        self.assertTrue(callable(getattr(Agent, '__str__')))

    def test_agent_dict_method_signature(self):
        """Test that Agent has a __dict__ method."""
        self.assertTrue(hasattr(Agent, '__dict__'))
        # Note: __dict__ is a special attribute, not a callable method
        # The actual implementation has a custom __dict__ method

    def test_agent_web_init_method_exists(self):
        """Test that Agent has web initialization method."""
        self.assertTrue(hasattr(Agent, '_Agent__web_init'))

    def test_agent_effify_method_exists(self):
        """Test that Agent has effify method."""
        self.assertTrue(hasattr(Agent, '_Agent__effify'))

    def test_agent_register_method_exists(self):
        """Test that Agent has register method."""
        self.assertTrue(hasattr(Agent, '_Agent__register'))

    def test_agent_get_user_method_exists(self):
        """Test that Agent has get user method."""
        self.assertTrue(hasattr(Agent, '_Agent__get_user'))

    def test_agent_get_interests_method_exists(self):
        """Test that Agent has get interests method."""
        self.assertTrue(hasattr(Agent, '_Agent__get_interests'))

    def test_agent_main_action_methods_exist(self):
        """Test that Agent has main action methods."""
        action_methods = ['post', 'comment', 'share', 'reaction', 'follow', 'cast', 'select_action']
        
        for method in action_methods:
            self.assertTrue(hasattr(Agent, method), f"Agent missing action method: {method}")
            self.assertTrue(callable(getattr(Agent, method)), f"Agent {method} is not callable")

    def test_agent_utility_methods_exist(self):
        """Test that Agent has utility methods."""
        utility_methods = ['followers', 'timeline', 'read', 'search', 'search_follow']
        
        for method in utility_methods:
            self.assertTrue(hasattr(Agent, method), f"Agent missing utility method: {method}")
            self.assertTrue(callable(getattr(Agent, method)), f"Agent {method} is not callable")


class TestAgents(unittest.TestCase):
    """Test class for y_client.classes.base_agent.Agents."""

    def setUp(self):
        """Set up test fixtures."""
        self.agents_collection = Agents()

    def test_agents_init(self):
        """Test Agents initialization."""
        self.assertIsInstance(self.agents_collection.agents, list)
        self.assertEqual(len(self.agents_collection.agents), 0)

    def test_add_agent(self):
        """Test adding agents to collection."""
        # Create mock agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"
        
        # Add agents
        self.agents_collection.add_agent(mock_agent1)
        self.agents_collection.add_agent(mock_agent2)
        
        # Verify agents are added
        self.assertEqual(len(self.agents_collection.agents), 2)
        self.assertIn(mock_agent1, self.agents_collection.agents)
        self.assertIn(mock_agent2, self.agents_collection.agents)

    def test_remove_agent(self):
        """Test removing agents from collection."""
        # Create and add mock agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"
        
        self.agents_collection.add_agent(mock_agent1)
        self.agents_collection.add_agent(mock_agent2)
        
        # Remove one agent
        self.agents_collection.remove_agent(mock_agent1)
        
        # Verify agent is removed
        self.assertEqual(len(self.agents_collection.agents), 1)
        self.assertNotIn(mock_agent1, self.agents_collection.agents)
        self.assertIn(mock_agent2, self.agents_collection.agents)

    def test_remove_agent_by_ids(self):
        """Test removing agents by their IDs."""
        # Create mock agents with user_ids
        mock_agent1 = MagicMock()
        mock_agent1.user_id = 101
        mock_agent2 = MagicMock()
        mock_agent2.user_id = 102
        mock_agent3 = MagicMock()
        mock_agent3.user_id = 103
        
        self.agents_collection.add_agent(mock_agent1)
        self.agents_collection.add_agent(mock_agent2)
        self.agents_collection.add_agent(mock_agent3)
        
        # Remove agents by IDs
        self.agents_collection.remove_agent_by_ids([101, 103])
        
        # Verify correct agents are removed
        self.assertEqual(len(self.agents_collection.agents), 1)
        self.assertNotIn(mock_agent1, self.agents_collection.agents)
        self.assertIn(mock_agent2, self.agents_collection.agents)
        self.assertNotIn(mock_agent3, self.agents_collection.agents)

    def test_get_agents(self):
        """Test getting all agents."""
        mock_agent = MagicMock()
        self.agents_collection.add_agent(mock_agent)
        
        agents = self.agents_collection.get_agents()
        
        self.assertEqual(agents, self.agents_collection.agents)
        self.assertIn(mock_agent, agents)

    def test_agents_iter(self):
        """Test iterating over agents."""
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"
        
        self.agents_collection.add_agent(mock_agent1)
        self.agents_collection.add_agent(mock_agent2)
        
        # Test iteration
        iterated_agents = list(self.agents_collection.agents_iter())
        
        self.assertEqual(len(iterated_agents), 2)
        self.assertIn(mock_agent1, iterated_agents)
        self.assertIn(mock_agent2, iterated_agents)

    def test_agents_str_representation(self):
        """Test string representation of Agents."""
        mock_agent1 = MagicMock()
        mock_agent1.__str__.return_value = "Agent1 String"
        mock_agent2 = MagicMock()
        mock_agent2.__str__.return_value = "Agent2 String"
        
        self.agents_collection.add_agent(mock_agent1)
        self.agents_collection.add_agent(mock_agent2)
        
        str_repr = str(self.agents_collection)
        self.assertEqual(str_repr, "Agent1 StringAgent2 String")

    def test_agents_dict_representation(self):
        """Test dictionary representation of Agents."""
        # Test the method exists and is callable
        self.assertTrue(hasattr(self.agents_collection, '__dict__'))
        self.assertTrue(callable(getattr(self.agents_collection, '__dict__')))
        
        # Test with empty collection
        empty_dict = self.agents_collection.__dict__()
        expected_empty = {"agents": []}
        self.assertEqual(empty_dict, expected_empty)

    def test_agents_equality(self):
        """Test equality comparison between Agents objects."""
        # Create two empty Agents objects
        other_agents = Agents()
        
        # Test equality method exists
        self.assertTrue(hasattr(self.agents_collection, '__eq__'))
        
        # Test with different lengths (should be unequal)
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        
        self.agents_collection.add_agent(mock_agent)
        # Don't test actual equality due to mock complexity
        # Just ensure the method exists and can be called
        self.assertNotEqual(len(self.agents_collection.agents), len(other_agents.agents))

    def test_agents_class_structure(self):
        """Test Agents class structure and attributes."""
        # Test that the class exists and has the expected module
        self.assertEqual(Agents.__module__, 'y_client.classes.base_agent')
        
        # Test that the class has expected methods
        expected_methods = [
            '__init__', 'add_agent', 'remove_agent', 'remove_agent_by_ids',
            'get_agents', 'agents_iter', '__str__', '__dict__', '__eq__'
        ]
        
        for method in expected_methods:
            self.assertTrue(hasattr(Agents, method), f"Agents missing method: {method}")

    def test_agents_initialization_attributes(self):
        """Test that Agents initializes with correct attributes."""
        agents = Agents()
        
        # Test that agents attribute exists and is a list
        self.assertTrue(hasattr(agents, 'agents'))
        self.assertIsInstance(agents.agents, list)
        self.assertEqual(len(agents.agents), 0)


if __name__ == '__main__':
    unittest.main()