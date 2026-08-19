"""Unit tests for bluetoothctl_parser.py — no xbmc/subprocess dependency."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

from bluetoothctl_parser import parse_battery_percentage, parse_connected  # noqa: E402

REALISTIC_INFO_OUTPUT = """Device 10:BF:67:30:D8:09 (public)
\tName: Amazon Remote
\tAlias: Amazon Remote
\tPaired: yes
\tBonded: yes
\tTrusted: yes
\tBlocked: no
\tConnected: yes
\tLegacyPairing: no
\tUUID: Human Interface Device    (00001812-0000-1000-8000-00805f9b34fb)
\tBattery Percentage: 0x5f (95)
"""


class ParseBatteryPercentageTests(unittest.TestCase):
    def test_extracts_value_from_realistic_multiline_output(self):
        self.assertEqual(parse_battery_percentage(REALISTIC_INFO_OUTPUT), 95)

    def test_returns_none_when_line_absent(self):
        output = "Device 10:BF:67:30:D8:09 (public)\n\tName: Amazon Remote\n\tConnected: yes\n"
        self.assertIsNone(parse_battery_percentage(output))

    def test_returns_none_for_empty_or_none_input(self):
        self.assertIsNone(parse_battery_percentage(''))
        self.assertIsNone(parse_battery_percentage(None))


class ParseConnectedTests(unittest.TestCase):
    def test_returns_true_when_connected(self):
        self.assertTrue(parse_connected(REALISTIC_INFO_OUTPUT))

    def test_returns_false_when_not_connected(self):
        output = REALISTIC_INFO_OUTPUT.replace('Connected: yes', 'Connected: no')
        self.assertFalse(parse_connected(output))

    def test_returns_none_when_line_absent(self):
        output = "Device 10:BF:67:30:D8:09 (public)\n\tName: Amazon Remote\n"
        self.assertIsNone(parse_connected(output))


if __name__ == '__main__':
    unittest.main()
