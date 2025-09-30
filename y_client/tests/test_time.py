#!/usr/bin/env python3
"""
Unit tests for y_client/classes/time.py module.

This module tests the SimulationSlot class for time management functionality.
Tests focus on the core functionalities that can be reliably tested.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from y_client.classes.time import SimulationSlot


class TestSimulationSlot(unittest.TestCase):
    """Test class for y_client.classes.time.SimulationSlot."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = {
            "servers": {
                "api": "http://localhost:8000/"
            }
        }
        
        self.mock_response_data = {
            "day": 1,
            "round": 5,
            "id": 29
        }

    @patch('y_client.classes.time.get')
    def test_get_current_slot(self, mock_get):
        """Test get_current_slot method."""
        # Mock initial response for __init__
        mock_response_init = MagicMock()
        mock_response_init.__dict__ = {"_content": json.dumps(self.mock_response_data).encode("utf-8")}
        
        # Mock updated response for get_current_slot
        updated_data = {"day": 2, "round": 10, "id": 58}
        mock_response_updated = MagicMock()
        mock_response_updated.__dict__ = {"_content": json.dumps(updated_data).encode("utf-8")}
        
        mock_get.side_effect = [mock_response_init, mock_response_updated]
        
        # Create SimulationSlot and call get_current_slot
        slot = SimulationSlot(self.mock_config)
        slot_id, day, slot_num = slot.get_current_slot()
        
        # Verify return values
        self.assertEqual(slot_id, 58)
        self.assertEqual(day, 2)
        self.assertEqual(slot_num, 10)
        
        # Verify instance attributes were updated
        self.assertEqual(slot.day, 2)
        self.assertEqual(slot.slot, 10)
        self.assertEqual(slot.id, 58)
        
        # Verify API was called twice
        self.assertEqual(mock_get.call_count, 2)

    @patch('y_client.classes.time.get')
    def test_config_missing_api_key(self, mock_get):
        """Test behavior when API config is missing."""
        config_no_api = {"servers": {}}
        
        # Should raise KeyError for missing 'api' key before any HTTP calls
        with self.assertRaises(KeyError):
            SimulationSlot(config_no_api)

    @patch('y_client.classes.time.get')
    def test_basic_slot_tracking(self, mock_get):
        """Test basic slot and day tracking through multiple operations."""
        # Set up a sequence of responses
        responses_data = [
            {"day": 1, "round": 0, "id": 1},   # Initial
            {"day": 1, "round": 5, "id": 6},   # After some time
            {"day": 2, "round": 0, "id": 25},  # Next day
        ]
        
        responses = []
        for data in responses_data:
            mock_response = MagicMock()
            mock_response.__dict__ = {"_content": json.dumps(data).encode("utf-8")}
            responses.append(mock_response)
        
        mock_get.side_effect = responses
        
        # Create and test slot
        slot = SimulationSlot(self.mock_config)
        self.assertEqual(slot.day, 1)
        self.assertEqual(slot.slot, 0)
        self.assertEqual(slot.id, 1)
        
        # Call get_current_slot to update
        slot_id, day, slot_num = slot.get_current_slot()
        self.assertEqual(day, 1)
        self.assertEqual(slot_num, 5)
        self.assertEqual(slot_id, 6)
        
        # Call again for next day
        slot_id, day, slot_num = slot.get_current_slot()
        self.assertEqual(day, 2)
        self.assertEqual(slot_num, 0)
        self.assertEqual(slot_id, 25)

    def test_simulation_slot_constants(self):
        """Test SimulationSlot class constants and basic structure."""
        # Test that the class exists and has the expected module
        self.assertEqual(SimulationSlot.__module__, 'y_client.classes.time')
        
        # Test that the class is properly defined
        self.assertTrue(hasattr(SimulationSlot, '__init__'))
        self.assertTrue(hasattr(SimulationSlot, 'get_current_slot'))
        self.assertTrue(hasattr(SimulationSlot, 'increment_slot'))


if __name__ == '__main__':
    unittest.main()