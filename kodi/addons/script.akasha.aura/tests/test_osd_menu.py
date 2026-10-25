"""Unit tests for osd_menu.py pure helpers (B14 chapters).

Stubs follow the same pattern as test_aura_detail/test_up_next: bare
xbmc modules are enough here -- only the pure chapter helpers are
exercised, never the dialog class.
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

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


if __name__ == '__main__':
    unittest.main()
