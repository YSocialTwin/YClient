#!/usr/bin/env python3
"""
Unit tests for y_client/clients/client_base.py module.

This module tests the YClientBase class for core client functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestYClientBase(unittest.TestCase):
    """Test class for y_client.clients.client_base.YClientBase."""

    def test_client_base_file_exists(self):
        """Test that client_base.py file exists."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        self.assertTrue(os.path.exists(file_path), "client_base.py file does not exist")

    def test_client_base_file_structure(self):
        """Test that client_base.py has expected structure."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for class definition
        self.assertIn('class YClientBase', content, "YClientBase class not found in file")
        
        # Check for key methods
        expected_methods = [
            '__init__', 'reset_news_db', 'reset_experiment', 'load_rrs_endpoints',
            'set_interests', 'set_recsys', 'add_agent', 'create_initial_population',
            'save_agents', 'load_existing_agents', 'churn', 'run_simulation'
        ]
        for method in expected_methods:
            self.assertIn(f'def {method}', content, f"Method {method} not found in YClientBase")

    def test_client_base_imports(self):
        """Test that client_base.py has correct imports."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required imports
        expected_imports = [
            'import random', 'import tqdm', 'import sys', 'import os', 'import networkx as nx',
            'from y_client import Agent, Agents, SimulationSlot',
            'from y_client.recsys import *',
            'from y_client.utils import generate_user'
        ]
        for import_stmt in expected_imports:
            self.assertIn(import_stmt, content, f"Import '{import_stmt}' not found in client_base.py")

    def test_client_base_init_method(self):
        """Test that YClientBase has proper __init__ method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __init__ method with correct parameters
        self.assertIn('def __init__(', content, "YClientBase __init__ method not found")
        self.assertIn('config_filename', content, "__init__ missing config_filename parameter")
        self.assertIn('prompts_filename', content, "__init__ missing prompts_filename parameter")
        self.assertIn('agents_filename', content, "__init__ missing agents_filename parameter")

    def test_client_base_reset_news_db_static_method(self):
        """Test that YClientBase has reset_news_db static method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for static method decorator and method
        self.assertIn('@staticmethod', content, "reset_news_db is not marked as static method")
        self.assertIn('def reset_news_db(', content, "reset_news_db method not found")

    def test_client_base_simulation_methods(self):
        """Test that YClientBase has simulation-related methods."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for simulation methods
        simulation_methods = ['run_simulation', 'create_initial_population', 'churn']
        for method in simulation_methods:
            self.assertIn(f'def {method}(self', content, f"{method} method not found")

    def test_client_base_agent_management_methods(self):
        """Test that YClientBase has agent management methods."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for agent management methods
        agent_methods = ['add_agent', 'save_agents', 'load_existing_agents']
        for method in agent_methods:
            self.assertIn(f'def {method}(self', content, f"{method} method not found")

    def test_client_base_recsys_methods(self):
        """Test that YClientBase has recommendation system methods."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for recsys methods
        self.assertIn('def set_recsys(self', content, "set_recsys method not found")
        self.assertIn('c_recsys', content, "set_recsys missing c_recsys parameter")
        self.assertIn('f_recsys', content, "set_recsys missing f_recsys parameter")

    def test_client_base_configuration_loading(self):
        """Test that YClientBase loads configuration properly."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for configuration loading
        self.assertIn('json.load(open(config_filename', content, "Config file loading not found")
        self.assertIn('json.load(open(prompts_filename', content, "Prompts file loading not found")

    def test_client_base_exception_handling(self):
        """Test that YClientBase has proper exception handling."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for exception handling
        self.assertIn('raise Exception("Prompts file not found")', content, 
                     "Exception handling for missing prompts file not found")

    def test_client_base_simulation_clock_initialization(self):
        """Test that YClientBase initializes simulation clock."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for simulation clock
        self.assertIn('SimulationSlot(self.config)', content, "Simulation clock initialization not found")
        self.assertIn('self.sim_clock', content, "sim_clock attribute not found")

    def test_client_base_agents_initialization(self):
        """Test that YClientBase initializes agents collection."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for agents initialization
        self.assertIn('self.agents = Agents()', content, "Agents collection initialization not found")

    def test_client_base_feed_initialization(self):
        """Test that YClientBase initializes feeds."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for feeds initialization
        self.assertIn('self.feed = Feeds()', content, "Feeds initialization not found")

    def test_client_base_graph_handling(self):
        """Test that YClientBase handles network graphs."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for graph handling
        self.assertIn('nx.read_edgelist', content, "NetworkX graph reading not found")
        self.assertIn('nx.convert_node_labels_to_integers', content, 
                     "Graph node label conversion not found")

    def test_client_base_rss_feed_loading(self):
        """Test that YClientBase can load RSS feeds."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for RSS feed loading
        self.assertIn('def load_rrs_endpoints(self, filename)', content, 
                     "load_rrs_endpoints method not found")
        self.assertIn('self.feed.add_feed', content, "Feed addition not found")

    def test_client_base_interests_management(self):
        """Test that YClientBase manages interests."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for interests management
        self.assertIn('def set_interests(self)', content, "set_interests method not found")
        self.assertIn('set_interests', content, "Interest setting not found")

    def test_client_base_api_interactions(self):
        """Test that YClientBase makes API calls."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for API interactions (post function is used but imported elsewhere)
        self.assertIn('api_url', content, "API URL handling not found")
        self.assertIn('}reset', content, "Reset endpoint not found")
        self.assertIn('/churn', content, "Churn endpoint not found")

    def test_client_base_simulation_parameters(self):
        """Test that YClientBase extracts simulation parameters."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for simulation parameters
        sim_params = [
            'self.days', 'self.slots', 'self.n_agents', 
            'self.percentage_new_agents_iteration', 'self.hourly_activity'
        ]
        for param in sim_params:
            self.assertIn(param, content, f"Simulation parameter {param} not found")

    def test_client_base_database_operations(self):
        """Test that YClientBase performs database operations."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for database operations
        self.assertIn('session.query(Articles).delete()', content, 
                     "Articles deletion not found")
        self.assertIn('session.query(Websites).delete()', content, 
                     "Websites deletion not found")
        self.assertIn('session.commit()', content, "Database commit not found")

    def test_client_base_json_operations(self):
        """Test that YClientBase uses JSON operations."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for JSON operations
        self.assertIn('json.load', content, "JSON loading not found")
        self.assertIn('json.dump', content, "JSON dumping not found")
        self.assertIn('json.dumps', content, "JSON string dumping not found")

    def test_client_base_agent_generation(self):
        """Test that YClientBase generates agents."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for agent generation
        self.assertIn('generate_user(self.config', content, "User generation not found")
        self.assertIn('agent.set_prompts', content, "Prompt setting not found")
        self.assertIn('agent.set_rec_sys', content, "Recommendation system setting not found")

    def test_client_base_simulation_loop(self):
        """Test that YClientBase has simulation loop."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for simulation loop components
        self.assertIn('for day in tqdm.tqdm(range(self.days))', content, 
                     "Daily simulation loop not found")
        self.assertIn('for _ in tqdm.tqdm(range(self.slots))', content, 
                     "Slot simulation loop not found")
        self.assertIn('random.sample(self.agents.agents', content, 
                     "Agent sampling not found")

    def test_client_base_activity_management(self):
        """Test that YClientBase manages agent activity."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for activity management
        self.assertIn('expected_active_users', content, "Active user calculation not found")
        self.assertIn('daily_active', content, "Daily activity tracking not found")
        self.assertIn('self.hourly_activity', content, "Hourly activity not found")

    def test_client_base_action_selection(self):
        """Test that YClientBase handles action selection."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'client_base.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for action selection
        self.assertIn('self.actions_likelihood', content, "Action likelihood not found")
        self.assertIn('random.choices', content, "Random action selection not found")
        self.assertIn('g.select_action', content, "Agent action selection not found")

    def test_client_base_required_modules(self):
        """Test that required modules are available."""
        # Test basic modules
        import random
        import sys
        import os
        import json
        
        # Test that basic functionality works
        test_data = {"test": "value"}
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)
        self.assertEqual(test_data, parsed_data)
        
        # Test random functionality
        self.assertIsInstance(random.random(), float)


if __name__ == '__main__':
    unittest.main()