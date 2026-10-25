"""Plex option sheet (context_sheet): entry composition + actions."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'resources', 'lib'))

import test_aura_detail  # noqa: F401 -- installs the fake xbmc modules

import context_sheet


class _Client:
    server_url = 'http://srv'
    token = 'tok'

    def __init__(self):
        self.scrobbled = []
        self.unscrobbled = []
        self.rated = []
        self.removed = []

    def scrobble(self, rk):
        self.scrobbled.append(rk)

    def unscrobble(self, rk):
        self.unscrobbled.append(rk)

    def rate(self, rk, score):
        self.rated.append((rk, score))

    def remove_from_continue_watching(self, rk):
        self.removed.append(rk)

    def metadata_item(self, rk):
        return {}


def _labels_shown(win, client, item, control_id=9999, **kw):
    """Run open_sheet, capture the labels shown to contextmenu."""
    captured = {}

    class FakeDialog:
        def contextmenu(self, labels):
            captured['labels'] = labels
            return -1

        def notification(self, *a):
            pass

        def select(self, *a):
            return -1

        def ok(self, *a):
            pass

    with patch.object(context_sheet.xbmcgui, 'Dialog',
                      return_value=FakeDialog()):
        context_sheet.open_sheet(win, client, item, control_id,
                                 lambda: None, **kw)
    return captured.get('labels', [])


def _win():
    win = MagicMock()
    win.getControl.return_value.getSelectedItem.return_value = MagicMock()
    win.getControl.return_value.getSelectedPosition.return_value = 0
    return win


class ContextSheetTests(unittest.TestCase):

    def setUp(self):
        # Which xbmc/xbmcgui stub is in place depends on test order --
        # pin the attributes so patch.object finds them regardless.
        context_sheet.xbmcgui.Dialog = MagicMock()
        context_sheet.xbmcgui.ListItem = \
            lambda *a, **k: MagicMock()
        context_sheet.xbmc.Player = MagicMock

    def test_movie_with_offset_entries(self):
        item = {'type': 'movie', 'rating_key': '1', 'part_key': '/p',
                'view_offset_ms': 5000, 'view_count': 0,
                'video_label': '1080p'}
        labels = _labels_shown(_win(), _Client(), item)
        # Resume + Restart + Open + RemoveCW + MarkWatched + Rate + Info
        self.assertEqual(len(labels), 7)

    def test_movie_without_offset_entries(self):
        item = {'type': 'movie', 'rating_key': '1', 'part_key': '/p',
                'view_count': 0, 'video_label': '1080p'}
        labels = _labels_shown(_win(), _Client(), item)
        # Play + Open + MarkWatched + Rate + Info (no resume/RemoveCW)
        self.assertEqual(len(labels), 5)

    def test_show_entries(self):
        item = {'type': 'show', 'rating_key': '1', 'view_count': 0}
        labels = _labels_shown(_win(), _Client(), item)
        # Open + MarkWatched + Rate
        self.assertEqual(len(labels), 3)

    def test_toggle_watched_flips_and_syncs_card(self):
        client = _Client()
        item = {'rating_key': '1', 'view_count': 0}
        win = _win()
        context_sheet.toggle_watched(win, client, item, 9999)
        self.assertEqual(client.scrobbled, ['1'])
        self.assertEqual(item['view_count'], 1)
        li = win.getControl(9999).getSelectedItem()
        li.getVideoInfoTag().setPlayCount.assert_called_with(1)

    def test_unwatch_uses_unscrobble(self):
        client = _Client()
        item = {'rating_key': '1', 'view_count': 3}
        context_sheet.toggle_watched(_win(), client, item, 9999)
        self.assertEqual(client.unscrobbled, ['1'])
        self.assertEqual(item['view_count'], 0)

    def test_remove_continue_watching(self):
        client = _Client()
        item = {'rating_key': '1', 'view_offset_ms': 5000}
        win = _win()
        removed = []
        context_sheet.remove_continue_watching(
            win, client, item, 9999, on_removed=removed.append)
        self.assertEqual(client.removed, ['1'])
        self.assertEqual(item['view_offset_ms'], 0)
        self.assertEqual(removed, [0])
        win.getControl(9999).removeItem.assert_called_with(0)

    def test_play_item_closes_and_flags_window(self):
        client = _Client()
        win = _win()
        item = {'type': 'movie', 'title': 'T', 'rating_key': '1',
                'part_key': '/library/parts/1'}
        with patch.object(context_sheet, 'osd_menu') as osd, \
             patch.object(context_sheet.xbmc, 'Player') as player:
            player.return_value = MagicMock()
            context_sheet.play_item(win, client, item)
        self.assertTrue(win.playback_started)
        self.assertEqual(win._playback_item['rating_key'], '1')
        win.close.assert_called_once()
        player.return_value.play.assert_called_once()
        osd.store_playback_context.assert_called_once()


if __name__ == '__main__':
    unittest.main()
