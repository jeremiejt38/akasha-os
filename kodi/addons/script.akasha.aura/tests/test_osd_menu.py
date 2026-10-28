"""Unit tests for osd_menu.py pure helpers (B14 chapters).

Stubs follow the same pattern as test_aura_detail/test_up_next: bare
xbmc modules are enough here -- only the pure chapter helpers are
exercised, never the dialog class.
"""

import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

for mod in ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs'):
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)
if not hasattr(sys.modules['xbmcgui'], 'WindowXMLDialog'):
    sys.modules['xbmcgui'].WindowXMLDialog = object

import osd_menu  # noqa: E402


class ChapterTimeTests(unittest.TestCase):

    def test_numeric_seconds(self):
        self.assertEqual(osd_menu._chapter_time_seconds(90), 90.0)
        self.assertEqual(osd_menu._chapter_time_seconds(0), 0.0)
        self.assertEqual(osd_menu._chapter_time_seconds(None), 0.0)

    def test_kodi_time_dict(self):
        t = {'hours': 1, 'minutes': 2, 'seconds': 3, 'milliseconds': 500}
        self.assertEqual(osd_menu._chapter_time_seconds(t), 3723)


class ChapterFormatTests(unittest.TestCase):

    def test_mm_ss(self):
        self.assertEqual(osd_menu._fmt_chapter_time(90), '1:30')
        self.assertEqual(osd_menu._fmt_chapter_time(600), '10:00')

    def test_h_mm_ss(self):
        self.assertEqual(osd_menu._fmt_chapter_time(3723), '1:02:03')

    def test_label_uses_name_and_time(self):
        label = osd_menu._chapter_label({'name': 'Intro', 'time': 5}, 0)
        self.assertEqual(label, 'Intro — 0:05')

    def test_label_falls_back_to_numbered(self):
        label = osd_menu._chapter_label({'name': '', 'time': 60}, 2)
        self.assertIn('3', label)
        self.assertTrue(label.endswith('1:00'))


class ChapterEntriesTests(unittest.TestCase):

    def setUp(self):
        self.chapters = [
            {'name': 'Cold open', 'time': 0},
            {'name': 'Act one', 'time': 300},
            {'name': 'Act two', 'time': 1200},
        ]

    def test_current_chapter_is_last_started(self):
        rows = osd_menu.chapter_entries(self.chapters, 700)
        self.assertEqual([r[2] for r in rows], [False, True, False])
        self.assertEqual(rows[1][1], 300.0)

    def test_before_first_chapter_marks_none(self):
        rows = osd_menu.chapter_entries(
            [{'name': 'A', 'time': 10}], 5)
        self.assertEqual([r[2] for r in rows], [False])

    def test_past_end_marks_last(self):
        rows = osd_menu.chapter_entries(self.chapters, 5000)
        self.assertEqual([r[2] for r in rows], [False, False, True])

    def test_empty_and_none(self):
        self.assertEqual(osd_menu.chapter_entries(None, 0), [])
        self.assertEqual(osd_menu.chapter_entries([], 0), [])


class _FakeHome:
    def __init__(self):
        self._props = {}

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')


class StoreChaptersTests(unittest.TestCase):

    def setUp(self):
        self.home = _FakeHome()
        self._patcher = patch.object(osd_menu, '_home', lambda: self.home)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_fetches_and_converts_to_seconds(self):
        client = MagicMock()
        client.item_chapters.return_value = [
            {'name': 'Intro', 'start_ms': 0, 'end_ms': 584208},
            {'name': 'Mid', 'start_ms': 584208, 'end_ms': 1200000},
        ]
        osd_menu.store_chapters(client, {'rating_key': '42'})
        stored = json.loads(self.home.getProperty(osd_menu.PROP_CHAPTERS))
        self.assertEqual(stored, [
            {'name': 'Intro', 'time': 0.0, 'thumb': ''},
            {'name': 'Mid', 'time': 584.208, 'thumb': ''}])
        client.item_chapters.assert_called_once_with('42')

    def test_builds_bif_thumb_url_from_part_key(self):
        client = MagicMock()
        client.server_url = 'https://plex.test'
        client.token = 'tok'
        client.item_chapters.return_value = [
            {'name': 'Intro', 'start_ms': 0, 'end_ms': 584208},
        ]
        osd_menu.store_chapters(client, {
            'rating_key': '42',
            'part_key': '/library/parts/123/abc/file.mkv'})
        stored = json.loads(self.home.getProperty(osd_menu.PROP_CHAPTERS))
        self.assertEqual(
            stored[0]['thumb'],
            'https://plex.test/library/parts/123/indexes/sd/0'
            '?X-Plex-Token=tok')

    def test_no_chapters_clears_property(self):
        self.home.setProperty(osd_menu.PROP_CHAPTERS, 'stale')
        client = MagicMock()
        client.item_chapters.return_value = []
        osd_menu.store_chapters(client, {'rating_key': '42'})
        self.assertEqual(self.home.getProperty(osd_menu.PROP_CHAPTERS), '')

    def test_client_without_support_clears_property(self):
        osd_menu.store_chapters(object(), {'rating_key': '42'})
        self.assertEqual(self.home.getProperty(osd_menu.PROP_CHAPTERS), '')

    def test_fetch_failure_clears_property(self):
        client = MagicMock()
        client.item_chapters.side_effect = RuntimeError('boom')
        osd_menu.store_chapters(client, {'rating_key': '42'})
        self.assertEqual(self.home.getProperty(osd_menu.PROP_CHAPTERS), '')


class CurrentChaptersTests(unittest.TestCase):

    def setUp(self):
        self.home = _FakeHome()
        self._patcher = patch.object(osd_menu, '_home', lambda: self.home)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_reads_stored_list(self):
        self.home.setProperty(osd_menu.PROP_CHAPTERS,
                              json.dumps([{'name': 'A', 'time': 10}]))
        self.assertEqual(osd_menu._current_chapters(),
                         [{'name': 'A', 'time': 10}])

    def test_empty_when_unset_or_broken(self):
        self.assertEqual(osd_menu._current_chapters(), [])
        self.home.setProperty(osd_menu.PROP_CHAPTERS, '{bad json')
        self.assertEqual(osd_menu._current_chapters(), [])
        self.home.setProperty(osd_menu.PROP_CHAPTERS, '{}')
        self.assertEqual(osd_menu._current_chapters(), [])


if __name__ == '__main__':
    unittest.main()
