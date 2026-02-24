from django.test import TestCase
from tickets.templatetags.custom_filters import compact_number

class CustomFiltersTest(TestCase):
    """Tests for the custom_filters template tags."""

    def test_compact_number_less_than_thousand(self):
        """Test formatting for numbers less than 1000."""
        self.assertEqual(compact_number(500), "500")
        self.assertEqual(compact_number(999), "999")
        self.assertEqual(compact_number(0), "0")

    def test_compact_number_thousands(self):
        """Test formatting for numbers in thousands."""
        self.assertEqual(compact_number(1000), "1k")
        self.assertEqual(compact_number(1500), "1.5k")
        self.assertEqual(compact_number(999999), "1000k")

    def test_compact_number_millions(self):
        """Test formatting for numbers in millions."""
        self.assertEqual(compact_number(1000000), "1m")
        self.assertEqual(compact_number(1500000), "1.5m")
        self.assertEqual(compact_number(999999999), "1000m")

    def test_compact_number_billions(self):
        """Test formatting for numbers in billions."""
        self.assertEqual(compact_number(1000000000), "1b")
        self.assertEqual(compact_number(1500000000), "1.5b")

    def test_compact_number_invalid_input(self):
        """Test formatting with invalid input (string, None)."""
        self.assertEqual(compact_number("invalid"), "invalid")
        self.assertEqual(compact_number(None), None)
