"""Unit tests for volume_router.py — no xbmc/subprocess dependency."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

from volume_router import (  # noqa: E402
    ACTIONS, VOLUME_DOWN, VOLUME_MUTE, VOLUME_UP, cec_volume_command, route,
)


class RouteTests(unittest.TestCase):
    def test_akasha_routes_to_kodi_builtins(self):
        executed = []
        route(VOLUME_UP, 'akasha', kodi_executebuiltin=executed.append)
        self.assertEqual(executed, ['VolumeUp'])
        route(VOLUME_DOWN, 'akasha', kodi_executebuiltin=executed.append)
        self.assertEqual(executed, ['VolumeUp', 'VolumeDown'])
        route(VOLUME_MUTE, 'akasha', kodi_executebuiltin=executed.append)
        self.assertEqual(executed, ['VolumeUp', 'VolumeDown', 'Mute'])

    def test_cec_routes_to_ui_commands(self):
        executed = []
        route(VOLUME_UP, 'cec', cec_run=executed.append)
        route(VOLUME_DOWN, 'cec', cec_run=executed.append)
        route(VOLUME_MUTE, 'cec', cec_run=executed.append)
        self.assertEqual(executed, ['volume-up', 'volume-down', 'mute'])

    def test_ir_mode_is_not_implemented(self):
        self.assertFalse(route(VOLUME_UP, 'ir'))

    def test_unknown_action_returns_false(self):
        self.assertFalse(route('unknown', 'akasha', kodi_executebuiltin=lambda x: None))

    def test_cec_command_format(self):
        cmd = cec_volume_command('volume-up', '/dev/cec0')
        self.assertEqual(cmd[0], 'cec-ctl')
        self.assertIn('--user-control-pressed', cmd)
        self.assertIn('ui-cmd=volume-up', cmd)


if __name__ == '__main__':
    unittest.main()
