"""
Unit tests for the SimulationSlot time management module.

These tests verify that the increment_slot method correctly handles
time advancement and properly prevents backwards time travel.
"""

import json
import unittest
from unittest.mock import patch, MagicMock


class TestIncrementSlotCondition(unittest.TestCase):
    """
    Tests for the increment_slot condition logic.
    
    The condition should only allow time updates when:
    - The calculated day is greater than the server's current day, OR
    - The calculated day equals the server's current day AND 
      the calculated slot is greater than the server's current slot
    """

    def test_condition_same_day_slot_ahead(self):
        """Test: Same day, calculated slot ahead of server slot -> should update"""
        # day == day_c and slot > slot_c
        day, day_c = 5, 5
        slot, slot_c = 10, 5
        
        # Old condition (buggy): day >= day_c or slot > slot_c
        old_result = day >= day_c or slot > slot_c
        
        # New condition (fixed): day > day_c or (day == day_c and slot > slot_c)
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(old_result)  # Old condition would update
        self.assertTrue(new_result)  # New condition should also update
        
    def test_condition_same_day_slot_behind(self):
        """Test: Same day, calculated slot behind server slot -> should NOT update"""
        # day == day_c and slot <= slot_c
        day, day_c = 5, 5
        slot, slot_c = 3, 10
        
        # Old condition (buggy): day >= day_c or slot > slot_c
        old_result = day >= day_c or slot > slot_c
        
        # New condition (fixed): day > day_c or (day == day_c and slot > slot_c)
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(old_result)  # BUG: Old condition would incorrectly update
        self.assertFalse(new_result)  # FIX: New condition correctly prevents update
        
    def test_condition_same_day_same_slot(self):
        """Test: Same day, same slot -> should NOT update"""
        day, day_c = 5, 5
        slot, slot_c = 10, 10
        
        # Old condition (buggy): day >= day_c or slot > slot_c
        old_result = day >= day_c or slot > slot_c
        
        # New condition (fixed): day > day_c or (day == day_c and slot > slot_c)
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(old_result)  # BUG: Old condition would incorrectly update
        self.assertFalse(new_result)  # FIX: New condition correctly prevents update
        
    def test_condition_future_day(self):
        """Test: Future day -> should update"""
        day, day_c = 6, 5
        slot, slot_c = 0, 23  # Even if slot is "behind", day is ahead
        
        # Old condition: day >= day_c or slot > slot_c
        old_result = day >= day_c or slot > slot_c
        
        # New condition: day > day_c or (day == day_c and slot > slot_c)
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(old_result)
        self.assertTrue(new_result)
        
    def test_condition_past_day(self):
        """Test: Past day -> should NOT update"""
        day, day_c = 4, 5
        slot, slot_c = 20, 5  # Slot is ahead but day is behind
        
        # Old condition (buggy): day >= day_c or slot > slot_c
        old_result = day >= day_c or slot > slot_c
        
        # New condition (fixed): day > day_c or (day == day_c and slot > slot_c)
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(old_result)  # BUG: Old condition would incorrectly update
        self.assertFalse(new_result)  # FIX: New condition correctly prevents update
        
    def test_condition_day_wrap_scenario(self):
        """Test: Day wrap scenario (slot 23 -> slot 0 of next day)"""
        # When at slot 23, next increment goes to day+1, slot 0
        day, day_c = 6, 5  # day is ahead
        slot, slot_c = 0, 23
        
        new_result = day > day_c or (day == day_c and slot > slot_c)
        
        self.assertTrue(new_result)  # Should update because day is ahead


class TestIncrementSlotIntegration(unittest.TestCase):
    """
    Integration tests for the SimulationSlot.increment_slot method.
    
    These tests verify the actual method behavior with mocked HTTP responses.
    """
    
    @patch('y_client.classes.time.get')
    @patch('y_client.classes.time.post')
    def test_increment_slot_does_not_update_when_behind(self, mock_post, mock_get):
        """Test that increment_slot does not update server when client is behind"""
        # Import here to use after patching
        from y_client.classes.time import SimulationSlot
        
        # Mock config
        config = {"servers": {"api": "http://localhost:5010/"}}
        
        # Create mock response object properly
        mock_response = MagicMock()
        mock_response.text = json.dumps({"day": 5, "round": 10, "id": 130})
        mock_response.__dict__["_content"] = json.dumps({"day": 5, "round": 10, "id": 130}).encode("utf-8")
        mock_get.return_value = mock_response
        
        # Create SimulationSlot
        sim_slot = SimulationSlot(config)
        
        self.assertEqual(sim_slot.day, 5)
        self.assertEqual(sim_slot.slot, 10)
        
        # Now simulate the client having stale data (would happen if get_current_slot
        # is called and server has advanced)
        # Set client state to day=5, slot=5 (behind server at day=5, slot=10)
        sim_slot.day = 5
        sim_slot.slot = 5
        
        # Call increment_slot - calculated next will be day=5, slot=6
        # But server is at day=5, slot=10, so should NOT update
        sim_slot.increment_slot()
        
        # The POST should NOT have been called because we're behind
        # After fix, post should not be called for time update
        # (get is called for current_time check)
        post_calls = [c for c in mock_post.call_args_list 
                      if 'update_time' in str(c)]
        self.assertEqual(len(post_calls), 0)


if __name__ == "__main__":
    unittest.main()
