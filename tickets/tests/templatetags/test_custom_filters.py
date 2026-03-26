from django.test import TestCase
from tickets.templatetags.custom_filters import compact_number

class CustomFiltersTest(TestCase):
    """Tests for the custom_filters template tags."""

    def test_compact_number_formatting(self):
        """Test formatting sizes across hundreds, thousands, millions, and billions."""
        # Hundreds
        self.assertEqual(compact_number(500), "500")
        self.assertEqual(compact_number(999), "999")
        
        # Thousands
        self.assertEqual(compact_number(1000), "1k")
        self.assertEqual(compact_number(1500), "1.5k")
        
        # Millions
        self.assertEqual(compact_number(1000000), "1m")
        self.assertEqual(compact_number(1500000), "1.5m")
        
        # Billions
        self.assertEqual(compact_number(1000000000), "1b")
        self.assertEqual(compact_number(1500000000), "1.5b")

    def test_compact_number_invalid_input(self):
        """Test formatting with invalid input gracefully returns input."""
        self.assertEqual(compact_number("invalid"), "invalid")
        self.assertEqual(compact_number(None), None)