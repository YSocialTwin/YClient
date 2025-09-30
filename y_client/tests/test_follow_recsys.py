#!/usr/bin/env python3
"""
Unit tests for y_client/recsys/FollowRecSys.py module.

This module tests the FollowRecSys class and its subclasses for follow recommendation functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from y_client.recsys.FollowRecSys import FollowRecSys, CommonNeighbors, Jaccard, AdamicAdar, PreferentialAttachment


class TestFollowRecSys(unittest.TestCase):
    """Test class for y_client.recsys.FollowRecSys.FollowRecSys."""

    def setUp(self):
        """Set up test fixtures."""
        self.default_n_neighbors = 10
        self.default_leaning_bias = 1
        self.test_base_url = "http://localhost:8000"
        self.test_user_id = "user123"

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        recsys = FollowRecSys()
        
        # Verify default initialization
        self.assertEqual(recsys.name, "FollowRecSys")
        self.assertEqual(recsys.n_neighbors, 10)
        self.assertEqual(recsys.params["mode"], "random")
        self.assertEqual(recsys.params["n_neighbors"], 10)
        self.assertEqual(recsys.params["leaning_biased"], 1)
        self.assertNotIn("user_id", recsys.params)

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        custom_n_neighbors = 5
        custom_leaning_bias = 2
        
        recsys = FollowRecSys(n_neighbors=custom_n_neighbors, leaning_bias=custom_leaning_bias)
        
        # Verify custom initialization
        self.assertEqual(recsys.name, "FollowRecSys")
        self.assertEqual(recsys.n_neighbors, custom_n_neighbors)
        self.assertEqual(recsys.params["mode"], "random")
        self.assertEqual(recsys.params["n_neighbors"], custom_n_neighbors)
        self.assertEqual(recsys.params["leaning_biased"], custom_leaning_bias)

    def test_add_user_id(self):
        """Test adding user ID to parameters."""
        recsys = FollowRecSys()
        
        # Initially no user_id
        self.assertNotIn("user_id", recsys.params)
        
        # Add user ID
        recsys.add_user_id(self.test_user_id)
        
        # Verify user_id is added
        self.assertIn("user_id", recsys.params)
        self.assertEqual(recsys.params["user_id"], self.test_user_id)

    def test_class_structure(self):
        """Test FollowRecSys class structure and attributes."""
        # Test that the class exists and has the expected module
        self.assertEqual(FollowRecSys.__module__, 'y_client.recsys.FollowRecSys')
        
        # Test that the class is properly defined
        self.assertTrue(hasattr(FollowRecSys, '__init__'))
        self.assertTrue(hasattr(FollowRecSys, 'add_user_id'))
        self.assertTrue(hasattr(FollowRecSys, 'follow_suggestions'))
        
        # Test default attributes exist
        recsys = FollowRecSys()
        self.assertTrue(hasattr(recsys, 'name'))
        self.assertTrue(hasattr(recsys, 'params'))
        self.assertTrue(hasattr(recsys, 'n_neighbors'))
        self.assertIsInstance(recsys.params, dict)

    def test_parameter_types(self):
        """Test that parameters have correct types."""
        recsys = FollowRecSys(n_neighbors=15, leaning_bias=3)
        
        # Test parameter types
        self.assertIsInstance(recsys.params["n_neighbors"], int)
        self.assertIsInstance(recsys.params["mode"], str)
        self.assertIsInstance(recsys.params["leaning_biased"], int)
        self.assertIsInstance(recsys.n_neighbors, int)
        
        # Test values
        self.assertEqual(recsys.params["n_neighbors"], 15)
        self.assertEqual(recsys.params["leaning_biased"], 3)
        self.assertEqual(recsys.params["mode"], "random")
        self.assertEqual(recsys.n_neighbors, 15)

    def test_user_id_overwrite(self):
        """Test that user ID can be overwritten."""
        recsys = FollowRecSys()
        
        # Add initial user ID
        recsys.add_user_id("first_user")
        self.assertEqual(recsys.params["user_id"], "first_user")
        
        # Overwrite with new user ID
        recsys.add_user_id("second_user")
        self.assertEqual(recsys.params["user_id"], "second_user")

    def test_default_parameter_values(self):
        """Test that default parameter values are correct."""
        recsys = FollowRecSys()
        
        # Check all default values
        expected_defaults = {
            "mode": "random",
            "n_neighbors": 10,
            "leaning_biased": 1
        }
        
        for key, expected_value in expected_defaults.items():
            self.assertIn(key, recsys.params)
            self.assertEqual(recsys.params[key], expected_value)
        
        # Verify user_id is not set by default
        self.assertNotIn("user_id", recsys.params)

    def test_parameter_persistence(self):
        """Test that parameters persist correctly across operations."""
        recsys = FollowRecSys(n_neighbors=8, leaning_bias=2)
        
        # Verify initial parameters
        self.assertEqual(recsys.params["n_neighbors"], 8)
        self.assertEqual(recsys.params["leaning_biased"], 2)
        
        # Add user ID
        recsys.add_user_id("persistent_user")
        
        # Verify all parameters are still correct
        self.assertEqual(recsys.params["n_neighbors"], 8)
        self.assertEqual(recsys.params["leaning_biased"], 2)
        self.assertEqual(recsys.params["user_id"], "persistent_user")
        self.assertEqual(recsys.params["mode"], "random")

    def test_name_attribute(self):
        """Test that the name attribute is set correctly."""
        recsys = FollowRecSys()
        self.assertEqual(recsys.name, "FollowRecSys")
        
        # Test with different parameters
        recsys2 = FollowRecSys(n_neighbors=15, leaning_bias=3)
        self.assertEqual(recsys2.name, "FollowRecSys")


class TestFollowRecSysSubclasses(unittest.TestCase):
    """Test the subclasses of FollowRecSys."""

    def test_common_neighbors_init(self):
        """Test CommonNeighbors initialization."""
        recsys = CommonNeighbors()
        
        self.assertEqual(recsys.name, "CommonNeighbors")
        self.assertEqual(recsys.params["mode"], "common_neighbors")
        self.assertEqual(recsys.params["n_neighbors"], 10)
        self.assertEqual(recsys.params["leaning_biased"], 1)

    def test_jaccard_init(self):
        """Test Jaccard initialization."""
        recsys = Jaccard()
        
        self.assertEqual(recsys.name, "Jaccard")
        self.assertEqual(recsys.params["mode"], "jaccard")
        self.assertEqual(recsys.params["n_neighbors"], 10)
        self.assertEqual(recsys.params["leaning_biased"], 1)

    def test_adamic_adar_init(self):
        """Test AdamicAdar initialization."""
        recsys = AdamicAdar()
        
        self.assertEqual(recsys.name, "AdamicAdar")
        self.assertEqual(recsys.params["mode"], "adamic_adar")
        self.assertEqual(recsys.params["n_neighbors"], 10)
        self.assertEqual(recsys.params["leaning_biased"], 1)

    def test_preferential_attachment_init(self):
        """Test PreferentialAttachment initialization."""
        recsys = PreferentialAttachment()
        
        self.assertEqual(recsys.name, "PreferentialAttachment")
        self.assertEqual(recsys.params["mode"], "preferential_attachment")
        self.assertEqual(recsys.params["n_neighbors"], 10)
        self.assertEqual(recsys.params["leaning_biased"], 1)

    def test_subclass_inheritance(self):
        """Test that subclasses inherit properly from FollowRecSys."""
        subclasses = [CommonNeighbors, Jaccard, AdamicAdar, PreferentialAttachment]
        
        for subclass in subclasses:
            instance = subclass()
            
            # Test inheritance
            self.assertIsInstance(instance, FollowRecSys)
            
            # Test that methods are inherited
            self.assertTrue(hasattr(instance, 'add_user_id'))
            self.assertTrue(hasattr(instance, 'follow_suggestions'))
            
            # Test that add_user_id works
            instance.add_user_id("test_user")
            self.assertEqual(instance.params["user_id"], "test_user")

    def test_subclass_custom_parameters(self):
        """Test subclasses with custom parameters."""
        custom_neighbors = 5
        custom_bias = 2
        
        subclasses = [CommonNeighbors, Jaccard, AdamicAdar, PreferentialAttachment]
        
        for subclass in subclasses:
            instance = subclass(n_neighbors=custom_neighbors, leaning_bias=custom_bias)
            
            self.assertEqual(instance.n_neighbors, custom_neighbors)
            self.assertEqual(instance.params["n_neighbors"], custom_neighbors)
            self.assertEqual(instance.params["leaning_biased"], custom_bias)


if __name__ == '__main__':
    unittest.main()