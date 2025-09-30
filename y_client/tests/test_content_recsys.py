#!/usr/bin/env python3
"""
Unit tests for y_client/recsys/ContentRecSys.py module.

This module tests the ContentRecSys class for content recommendation functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from y_client.recsys.ContentRecSys import ContentRecSys


class TestContentRecSys(unittest.TestCase):
    """Test class for y_client.recsys.ContentRecSys.ContentRecSys."""

    def setUp(self):
        """Set up test fixtures."""
        self.default_n_posts = 10
        self.default_visibility_rounds = 36
        self.test_base_url = "http://localhost:8000"
        self.test_user_id = "user123"

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        recsys = ContentRecSys()
        
        # Verify default initialization
        self.assertEqual(recsys.name, "ContentRecSys")
        self.assertEqual(recsys.params["limit"], 10)
        self.assertEqual(recsys.params["mode"], "default")
        self.assertEqual(recsys.params["visibility_rounds"], 36)
        self.assertNotIn("uid", recsys.params)

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        custom_n_posts = 20
        custom_visibility_rounds = 48
        
        recsys = ContentRecSys(n_posts=custom_n_posts, visibility_rounds=custom_visibility_rounds)
        
        # Verify custom initialization
        self.assertEqual(recsys.name, "ContentRecSys")
        self.assertEqual(recsys.params["limit"], custom_n_posts)
        self.assertEqual(recsys.params["mode"], "default")
        self.assertEqual(recsys.params["visibility_rounds"], custom_visibility_rounds)

    def test_add_user_id(self):
        """Test adding user ID to parameters."""
        recsys = ContentRecSys()
        
        # Initially no uid
        self.assertNotIn("uid", recsys.params)
        
        # Add user ID
        recsys.add_user_id(self.test_user_id)
        
        # Verify uid is added
        self.assertIn("uid", recsys.params)
        self.assertEqual(recsys.params["uid"], self.test_user_id)

    def test_class_structure(self):
        """Test ContentRecSys class structure and attributes."""
        # Test that the class exists and has the expected module
        self.assertEqual(ContentRecSys.__module__, 'y_client.recsys.ContentRecSys')
        
        # Test that the class is properly defined
        self.assertTrue(hasattr(ContentRecSys, '__init__'))
        self.assertTrue(hasattr(ContentRecSys, 'add_user_id'))
        self.assertTrue(hasattr(ContentRecSys, 'read'))
        
        # Test default attributes exist
        recsys = ContentRecSys()
        self.assertTrue(hasattr(recsys, 'name'))
        self.assertTrue(hasattr(recsys, 'params'))
        self.assertIsInstance(recsys.params, dict)

    def test_parameter_types(self):
        """Test that parameters have correct types."""
        recsys = ContentRecSys(n_posts=15, visibility_rounds=50)
        
        # Test parameter types
        self.assertIsInstance(recsys.params["limit"], int)
        self.assertIsInstance(recsys.params["mode"], str)
        self.assertIsInstance(recsys.params["visibility_rounds"], int)
        
        # Test values
        self.assertEqual(recsys.params["limit"], 15)
        self.assertEqual(recsys.params["visibility_rounds"], 50)
        self.assertEqual(recsys.params["mode"], "default")

    def test_user_id_overwrite(self):
        """Test that user ID can be overwritten."""
        recsys = ContentRecSys()
        
        # Add initial user ID
        recsys.add_user_id("first_user")
        self.assertEqual(recsys.params["uid"], "first_user")
        
        # Overwrite with new user ID
        recsys.add_user_id("second_user")
        self.assertEqual(recsys.params["uid"], "second_user")

    def test_default_parameter_values(self):
        """Test that default parameter values are correct."""
        recsys = ContentRecSys()
        
        # Check all default values
        expected_defaults = {
            "limit": 10,
            "mode": "default",
            "visibility_rounds": 36
        }
        
        for key, expected_value in expected_defaults.items():
            self.assertIn(key, recsys.params)
            self.assertEqual(recsys.params[key], expected_value)
        
        # Verify uid is not set by default
        self.assertNotIn("uid", recsys.params)

    def test_parameter_persistence(self):
        """Test that parameters persist correctly across operations."""
        recsys = ContentRecSys(n_posts=25, visibility_rounds=60)
        
        # Verify initial parameters
        self.assertEqual(recsys.params["limit"], 25)
        self.assertEqual(recsys.params["visibility_rounds"], 60)
        
        # Add user ID
        recsys.add_user_id("persistent_user")
        
        # Verify all parameters are still correct
        self.assertEqual(recsys.params["limit"], 25)
        self.assertEqual(recsys.params["visibility_rounds"], 60)
        self.assertEqual(recsys.params["uid"], "persistent_user")
        self.assertEqual(recsys.params["mode"], "default")

    def test_name_attribute(self):
        """Test that the name attribute is set correctly."""
        recsys = ContentRecSys()
        self.assertEqual(recsys.name, "ContentRecSys")
        
        # Test with different parameters
        recsys2 = ContentRecSys(n_posts=5, visibility_rounds=12)
        self.assertEqual(recsys2.name, "ContentRecSys")


if __name__ == '__main__':
    unittest.main()