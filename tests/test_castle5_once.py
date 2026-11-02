"""Public one-shot executor safety checks; no browser or game access."""
import unittest
from unittest.mock import patch

from castle5_once import resource_debit_confirmed, validate_target


class CastleOnceSafetyTests(unittest.TestCase):
    def test_requires_explicit_kingsage_target(self):
        with patch('castle5_once.HOST', 's99-br.kingsage.gameforge.com'), patch('castle5_once.VILLAGE', '1234'):
            validate_target()
        with patch('castle5_once.HOST', 'example.net'), patch('castle5_once.VILLAGE', '1234'):
            with self.assertRaises(ValueError):
                validate_target()
        with patch('castle5_once.HOST', 's99-br.kingsage.gameforge.com'), patch('castle5_once.VILLAGE', ''):
            with self.assertRaises(ValueError):
                validate_target()

    def test_requires_debit_for_each_resource(self):
        before = {'wood': 300, 'stone': 300, 'iron': 300}
        cost = {'wood': 129, 'stone': 159, 'iron': 120}
        self.assertTrue(resource_debit_confirmed(before, {'wood': '171', 'stone': '141', 'iron': '180'}, cost))
        self.assertFalse(resource_debit_confirmed(before, {'wood': '300', 'stone': '141', 'iron': '180'}, cost))
        with self.assertRaises(ValueError):
            resource_debit_confirmed(before, {'wood': '', 'stone': '141', 'iron': '180'}, cost)


if __name__ == '__main__':
    unittest.main()
