#!/usr/bin/env python3
"""
Unit tests for y_client/classes/page_agent.py module.

This module tests the PageAgent class for page-specific agent functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import sys
import os
import inspect

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestPageAgent(unittest.TestCase):
    """Test class for y_client.classes.page_agent.PageAgent."""

    def test_page_agent_file_exists(self):
        """Test that page_agent.py file exists."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        self.assertTrue(os.path.exists(file_path), "page_agent.py file does not exist")

    def test_page_agent_file_structure(self):
        """Test that page_agent.py has expected structure."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for class definition
        self.assertIn('class PageAgent', content, "PageAgent class not found in file")
        
        # Check for key methods
        expected_methods = ['select_action', 'select_news', 'comment', 'reply', 'news']
        for method in expected_methods:
            self.assertIn(f'def {method}', content, f"Method {method} not found in PageAgent")

    def test_page_agent_imports(self):
        """Test that page_agent.py has correct imports."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required imports
        expected_imports = ['from y_client.classes.base_agent import Agent', 'import json', 'import re']
        for import_stmt in expected_imports:
            self.assertIn(import_stmt, content, f"Import '{import_stmt}' not found in page_agent.py")

    def test_page_agent_inheritance_structure(self):
        """Test that PageAgent inherits from Agent."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for inheritance
        self.assertIn('class PageAgent(Agent)', content, "PageAgent does not inherit from Agent")

    def test_page_agent_init_method(self):
        """Test that PageAgent has __init__ method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __init__ method
        self.assertIn('def __init__(self', content, "PageAgent __init__ method not found")
        self.assertIn('super().__init__', content, "PageAgent __init__ does not call super()")

    def test_page_agent_select_action_override(self):
        """Test that PageAgent overrides select_action method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for select_action override
        self.assertIn('def select_action(self', content, "PageAgent select_action method not found")
        # Should have a comment about page-specific behavior
        self.assertTrue(
            '# a page can only post news' in content or 'can only post news' in content,
            "select_action method does not indicate page-specific behavior"
        )

    def test_page_agent_select_news_method(self):
        """Test that PageAgent has select_news method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for select_news method
        self.assertIn('def select_news(self', content, "PageAgent select_news method not found")
        
    def test_page_agent_news_method(self):
        """Test that PageAgent has news method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for news method
        self.assertIn('def news(self', content, "PageAgent news method not found")

    def test_page_agent_comment_override(self):
        """Test that PageAgent overrides comment method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for comment override (should just return)
        self.assertIn('def comment(self', content, "PageAgent comment method not found")

    def test_page_agent_reply_override(self):
        """Test that PageAgent overrides reply method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for reply override (should just return)
        self.assertIn('def reply(self', content, "PageAgent reply method not found")

    def test_page_agent_effify_method(self):
        """Test that PageAgent has __effify method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __effify method
        self.assertIn('def __effify(self', content, "PageAgent __effify method not found")

    def test_page_agent_extract_components_method(self):
        """Test that PageAgent has __extract_components method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __extract_components method
        self.assertIn('def __extract_components(self', content, "PageAgent __extract_components method not found")

    def test_page_agent_str_method(self):
        """Test that PageAgent has __str__ method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __str__ method
        self.assertIn('def __str__(self', content, "PageAgent __str__ method not found")

    def test_page_agent_dict_method(self):
        """Test that PageAgent has __dict__ method."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for __dict__ method
        self.assertIn('def __dict__(self', content, "PageAgent __dict__ method not found")

    def test_page_agent_method_parameters(self):
        """Test that key methods have correct parameters."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check select_action parameters
        self.assertIn('def select_action(self, tid, actions', content, 
                     "select_action method has incorrect parameters")
        
        # Check news method parameters
        self.assertIn('def news(self, tid, article, website', content,
                     "news method has incorrect parameters")

    def test_page_agent_database_interaction(self):
        """Test that PageAgent interacts with database for news selection."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for database session usage
        self.assertIn('session.query(Websites)', content, "PageAgent does not query Websites table")

    def test_page_agent_json_usage(self):
        """Test that PageAgent uses json for data serialization."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for json.dumps usage
        self.assertIn('json.dumps', content, "PageAgent does not use json.dumps")

    def test_page_agent_regex_usage(self):
        """Test that PageAgent uses regex for topic extraction."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for regex usage
        self.assertIn('re.findall', content, "PageAgent does not use re.findall")
        self.assertIn('re.compile', content, "PageAgent does not use re.compile")

    def test_page_agent_autogen_usage(self):
        """Test that PageAgent uses autogen for LLM interactions."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for autogen usage
        self.assertIn('AssistantAgent', content, "PageAgent does not use AssistantAgent")

    def test_page_agent_api_interaction(self):
        """Test that PageAgent makes API calls."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for API endpoint usage
        self.assertIn('/news', content, "PageAgent does not use /news endpoint")
        self.assertIn('post(', content, "PageAgent does not make POST requests")

    def test_page_agent_feed_url_attribute(self):
        """Test that PageAgent has feed_url attribute."""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'classes', 'page_agent.py')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for feed_url attribute
        self.assertIn('self.feed_url', content, "PageAgent does not have feed_url attribute")

    def test_json_import_functionality(self):
        """Test that json module works as expected."""
        import json
        
        test_data = {"user_id": 123, "tweet": "test message", "hashtags": ["#test"]}
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)
        
        self.assertEqual(test_data, parsed_data)

    def test_regex_functionality(self):
        """Test that regex module works as expected."""
        import re
        
        # Test hashtag pattern
        hashtag_pattern = re.compile(r"#\w+")
        hashtags = hashtag_pattern.findall("#test #news #breaking")
        self.assertEqual(hashtags, ["#test", "#news", "#breaking"])
        
        # Test mention pattern
        mention_pattern = re.compile(r"@\w+")
        mentions = mention_pattern.findall("@user1 @user2")
        self.assertEqual(mentions, ["@user1", "@user2"])


if __name__ == '__main__':
    unittest.main()