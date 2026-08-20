import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cloud_gaming_filter import filter_services  # noqa: E402

SERVICES = [
    ('GeForce NOW', 'https://play.geforcenow.com'),
    ('Xbox Cloud Gaming', 'https://xbox.com/play'),
    ('Amazon Luna', 'https://luna.amazon.com'),
    ('Google Stadia (Boosteroid)', 'https://cloud.boosteroid.com'),
]


class FilterServicesTests(unittest.TestCase):
    def test_empty_csv_returns_all(self):
        self.assertEqual(filter_services(SERVICES, ''), SERVICES)

    def test_none_returns_all(self):
        self.assertEqual(filter_services(SERVICES, None), SERVICES)

    def test_blank_csv_returns_all(self):
        self.assertEqual(filter_services(SERVICES, '   ,  ,'), SERVICES)

    def test_single_exact_match(self):
        result = filter_services(SERVICES, 'GeForce NOW')
        self.assertEqual(result, [SERVICES[0]])

    def test_case_insensitive(self):
        result = filter_services(SERVICES, 'geforce now')
        self.assertEqual(result, [SERVICES[0]])

    def test_substring_match_for_boosteroid(self):
        result = filter_services(SERVICES, 'Boosteroid')
        self.assertEqual(result, [SERVICES[3]])

    def test_multiple_matches_preserve_original_order(self):
        result = filter_services(SERVICES, 'Amazon Luna,GeForce NOW')
        self.assertEqual(result, [SERVICES[0], SERVICES[2]])

    def test_no_match_falls_back_to_all(self):
        result = filter_services(SERVICES, 'Steam Link,Moonlight')
        self.assertEqual(result, SERVICES)


if __name__ == '__main__':
    unittest.main()
