"""
Unit tests for the logger module.

These tests verify the error logging functionality.
"""

import sys
import unittest
from io import StringIO
from unittest.mock import patch

from y_client.logger import log_error


class TestLogError(unittest.TestCase):
    """Tests for the log_error function."""

    def test_log_error_basic(self):
        """Test basic error logging to stderr."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            log_error("Test error message")
            output = mock_stderr.getvalue()
            
            self.assertIn("ERROR", output)
            self.assertIn("Test error message", output)
            self.assertIn("\n", output)  # Should end with newline

    def test_log_error_with_context(self):
        """Test error logging with context."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            log_error("Connection failed", context="load_agents")
            output = mock_stderr.getvalue()
            
            self.assertIn("ERROR", output)
            self.assertIn("load_agents", output)
            self.assertIn("Connection failed", output)

    def test_log_error_includes_timestamp(self):
        """Test that error logging includes a timestamp."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            log_error("Error with timestamp")
            output = mock_stderr.getvalue()
            
            # Timestamp format: [YYYY-MM-DD HH:MM:SS]
            self.assertIn("[", output)
            self.assertIn("]", output)
            # Check for date-like pattern
            self.assertRegex(output, r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')


if __name__ == "__main__":
    unittest.main()
