"""Unit tests for addons_inventory.py — no xbmc dependency."""

import json
import unittest

import addons_inventory


class TestParseGetAddonsResponse(unittest.TestCase):
    def test_filters_by_included_type(self):
        raw = json.dumps({
            'result': {
                'addons': [
                    {'addonid': 'script.cloud.gaming', 'name': 'Cloud Gaming',
                     'version': '1.0', 'summary': 'x', 'icon': '', 'type': 'xbmc.python.script'},
                    {'addonid': 'skin.arctic.horizon.two', 'name': 'Arctic Horizon 2',
                     'version': '2.0', 'summary': 'x', 'icon': '', 'type': 'xbmc.gui.skin'},
                    {'addonid': 'plugin.program.steamlink', 'name': 'Steam Link',
                     'version': '1.1', 'summary': 'x', 'icon': '', 'type': 'xbmc.python.pluginsource'},
                ]
            }
        })
        addons = addons_inventory.parse_get_addons_response(raw)
        ids = [a['addonid'] for a in addons]
        self.assertIn('script.cloud.gaming', ids)
        self.assertIn('plugin.program.steamlink', ids)
        self.assertNotIn('skin.arctic.horizon.two', ids)

    def test_excludes_akasha_own_addons(self):
        raw = json.dumps({
            'result': {
                'addons': [
                    {'addonid': 'script.akasha.aura', 'name': 'Akasha Aura',
                     'version': '1.0', 'summary': '', 'icon': '', 'type': 'xbmc.python.script'},
                ]
            }
        })
        addons = addons_inventory.parse_get_addons_response(raw)
        self.assertEqual(addons, [])

    def test_excludes_service_and_virtual_prefixes(self):
        raw = json.dumps({
            'result': {
                'addons': [
                    {'addonid': 'service.argononecontrol', 'name': 'Argon ONE',
                     'version': '1.0', 'summary': '', 'icon': '', 'type': 'xbmc.python.script'},
                    {'addonid': 'virtual.rpi-tools', 'name': 'RPi Tools',
                     'version': '1.0', 'summary': '', 'icon': '', 'type': 'xbmc.python.script'},
                    {'addonid': 'script.plexmod', 'name': 'Plex for Kodi',
                     'version': '1.0', 'summary': '', 'icon': '', 'type': 'xbmc.python.script'},
                ]
            }
        })
        addons = addons_inventory.parse_get_addons_response(raw)
        ids = [a['addonid'] for a in addons]
        self.assertEqual(ids, ['script.plexmod'])

    def test_malformed_json_returns_empty(self):
        self.assertEqual(addons_inventory.parse_get_addons_response('not json'), [])

    def test_missing_result_returns_empty(self):
        self.assertEqual(addons_inventory.parse_get_addons_response('{}'), [])


class TestPinnedPersistence(unittest.TestCase):
    def test_parse_pinned_handles_empty(self):
        self.assertEqual(addons_inventory.parse_pinned(''), [])
        self.assertEqual(addons_inventory.parse_pinned(None), [])

    def test_parse_pinned_splits_and_strips(self):
        self.assertEqual(
            addons_inventory.parse_pinned('a.b, c.d ,,e.f'),
            ['a.b', 'c.d', 'e.f'],
        )

    def test_serialize_pinned_roundtrip(self):
        ids = ['a.b', 'c.d']
        raw = addons_inventory.serialize_pinned(ids)
        self.assertEqual(addons_inventory.parse_pinned(raw), ids)

    def test_toggle_pinned_adds_and_removes(self):
        pinned = addons_inventory.toggle_pinned([], 'a.b')
        self.assertEqual(pinned, ['a.b'])
        pinned = addons_inventory.toggle_pinned(pinned, 'a.b')
        self.assertEqual(pinned, [])


class TestSortAddons(unittest.TestCase):
    def test_pinned_first_then_alphabetical(self):
        addons = [
            {'addonid': 'z.addon', 'name': 'Zeta'},
            {'addonid': 'a.addon', 'name': 'Alpha'},
            {'addonid': 'm.addon', 'name': 'Mu'},
        ]
        sorted_addons = addons_inventory.sort_addons(addons, ['m.addon'])
        self.assertEqual(
            [a['addonid'] for a in sorted_addons],
            ['m.addon', 'a.addon', 'z.addon'],
        )


if __name__ == '__main__':
    unittest.main()
