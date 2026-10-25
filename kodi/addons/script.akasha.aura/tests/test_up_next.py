"""Unit tests for up_next.py pure helpers (B1).

Same stub pattern as test_divert_state.py: xbmc/xbmcaddon/xbmcgui are
replaced before import, Window(10000) is a dict-backed fake so the
playback-context properties round-trip exactly like in Kodi.
"""

import json
import os
import sys
import threading
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        mock = MagicMock(name=name)
        setattr(self, name, mock)
        return mock


class FakeControl:
    def __init__(self, cid):
        self._cid = cid
        self.label = ''

    def setLabel(self, label):
        self.label = label

    def setImage(self, image):
        self.label = image

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeWindowXMLDialog:
    def __init__(self, *args, **kwargs):
        self._props = {}
        self._controls = {}
        self._focus = None
        self.closed = False

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')

    def getControl(self, cid):
        if cid not in self._controls:
            self._controls[cid] = FakeControl(cid)
        return self._controls[cid]

    def setFocusId(self, cid):
        self._focus = cid

    def close(self):
        self.closed = True


class FakeHomeWindow:
    """Dict-backed stand-in for xbmcgui.Window(10000)."""

    def __init__(self):
        self._props = {}

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')


_home = FakeHomeWindow()

xbmc = _StubModule('xbmc')
xbmcaddon = _StubModule('xbmcaddon')
xbmcaddon.Addon = MagicMock
xbmcgui = _StubModule('xbmcgui')
for _klass in ('WindowXMLDialog', 'WindowXML'):
    setattr(xbmcgui, _klass, FakeWindowXMLDialog)
xbmcgui.Window = lambda *args: _home
xbmcgui.ListItem = MagicMock
xbmcvfs = _StubModule('xbmcvfs')

sys.modules['xbmc'] = xbmc
sys.modules['xbmcaddon'] = xbmcaddon
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcvfs'] = xbmcvfs

import osd_menu  # noqa: E402
import up_next  # noqa: E402

# osd_menu may have been imported earlier in the suite bound to another
# test's bare stub modules; pinning the pieces it dereferences keeps
# these tests independent of import order.
osd_menu._home = lambda: _home
up_next._home = lambda: _home
_fake_player = MagicMock()
_fake_player.getPlayingFile.return_value = ''
osd_menu.xbmc.Player = lambda *args: _fake_player
osd_menu.xbmcgui.ACTION_PREVIOUS_MENU = 10
osd_menu.xbmcgui.ACTION_NAV_BACK = 92


def _queue_items():
    return [
        {'rating_key': '100', 'part_key': '/part/100', 'type': 'episode',
         'title': 'Ep1'},
        {'rating_key': '101', 'part_key': '/part/101', 'type': 'episode',
         'title': 'Ep2', 'show_title': 'Show', 'season': 1, 'index': 2},
        {'rating_key': '102', 'type': 'episode', 'title': 'Ep3'},
    ]


class StoreContextTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()

    def test_queue_prop_holds_items_after_current(self):
        client = MagicMock(server_url='http://srv', token='tk')
        osd_menu.store_playback_context(client, _queue_items())
        queue = json.loads(_home.getProperty(osd_menu.PROP_QUEUE))
        self.assertEqual([it['rating_key'] for it in queue], ['101', '102'])

    def test_queue_item_keeps_only_known_fields(self):
        client = MagicMock(server_url='http://srv', token='tk')
        items = _queue_items()
        items[1]['unknown_field'] = 'nope'
        osd_menu.store_playback_context(client, items)
        queue = json.loads(_home.getProperty(osd_menu.PROP_QUEUE))
        self.assertNotIn('unknown_field', queue[0])
        self.assertEqual(queue[0]['title'], 'Ep2')

    def test_single_item_writes_empty_queue(self):
        client = MagicMock(server_url='http://srv', token='tk')
        osd_menu.store_playback_context(client, [_queue_items()[0]])
        self.assertEqual(
            json.loads(_home.getProperty(osd_menu.PROP_QUEUE)), [])

    def test_part_map_still_covers_whole_queue(self):
        client = MagicMock(server_url='http://srv', token='tk')
        osd_menu.store_playback_context(client, _queue_items())
        mapping = json.loads(_home.getProperty(osd_menu.PROP_MAP))
        self.assertEqual(mapping['/part/100'], '100')
        self.assertEqual(mapping['/part/101'], '101')
        self.assertNotIn('/part/102', mapping)  # no part_key -> skipped


class QueueHelpersTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()

    def test_peek_returns_first_without_popping(self):
        _home.setProperty(osd_menu.PROP_QUEUE,
                          json.dumps([{'rating_key': '101'},
                                      {'rating_key': '102'}]))
        self.assertEqual(up_next.peek_queue()['rating_key'], '101')
        self.assertEqual(up_next.peek_queue()['rating_key'], '101')

    def test_pop_returns_first_and_rewrites(self):
        _home.setProperty(osd_menu.PROP_QUEUE,
                          json.dumps([{'rating_key': '101'},
                                      {'rating_key': '102'}]))
        self.assertEqual(up_next.pop_queue()['rating_key'], '101')
        self.assertEqual(up_next.peek_queue()['rating_key'], '102')

    def test_empty_and_corrupt_queue(self):
        self.assertIsNone(up_next.peek_queue())
        _home.setProperty(osd_menu.PROP_QUEUE, '{oops')
        self.assertIsNone(up_next.peek_queue())
        self.assertIsNone(up_next.pop_queue())


class NaturalEndTests(unittest.TestCase):

    def test_end_threshold(self):
        self.assertTrue(up_next.is_natural_end(0))
        self.assertTrue(up_next.is_natural_end(2.9))
        self.assertTrue(
            up_next.is_natural_end(up_next.NATURAL_END_REMAINING_SECONDS))
        self.assertFalse(up_next.is_natural_end(3.1))
        self.assertFalse(up_next.is_natural_end(None))


class StreamUrlTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _home.setProperty(osd_menu.PROP_SERVER, 'http://srv')
        _home.setProperty(osd_menu.PROP_TOKEN, 'tk')

    def test_builds_token_url(self):
        item = {'part_key': '/library/parts/99/file.mp4'}
        self.assertEqual(
            up_next._stream_url(item),
            'http://srv/library/parts/99/file.mp4?X-Plex-Token=tk')

    def test_ampersand_when_part_has_query(self):
        item = {'part_key': '/part/x?fmt=4'}
        self.assertTrue(
            up_next._stream_url(item).endswith('fmt=4&X-Plex-Token=tk'))

    def test_none_without_part_key(self):
        self.assertIsNone(up_next._stream_url({'rating_key': '1'}))


class HydrateTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _home.setProperty(osd_menu.PROP_SERVER, 'http://srv')
        _home.setProperty(osd_menu.PROP_TOKEN, 'tk')

    def test_skip_when_part_key_present(self):
        item = {'part_key': '/part/1'}
        self.assertIs(up_next._hydrate(item), item)

    def test_fetches_metadata_for_shallow_item(self):
        full = {'rating_key': '9', 'part_key': '/part/9', 'title': 'Full'}
        fake_client = MagicMock()
        fake_client.metadata_item.return_value = full
        fake_plex = MagicMock()
        fake_plex.PlexClient.return_value = fake_client
        old = sys.modules.get('plex_client')
        sys.modules['plex_client'] = fake_plex
        try:
            result = up_next._hydrate({'rating_key': '9', 'type': 'episode'})
        finally:
            if old is not None:
                sys.modules['plex_client'] = old
            else:
                del sys.modules['plex_client']
        fake_client.metadata_item.assert_called_once_with('9')
        self.assertEqual(result['part_key'], '/part/9')
        self.assertEqual(result['type'], 'episode')


class DialogTests(unittest.TestCase):

    def _dialog(self):
        dlg = up_next.AuraUpNextWindow.__new__(up_next.AuraUpNextWindow)
        FakeWindowXMLDialog.__init__(dlg)
        dlg.item = None
        dlg.result = 'cancel'
        dlg._stop = threading.Event()
        return dlg

    def test_play_button_confirms(self):
        dlg = self._dialog()
        dlg.onClick(up_next.PLAY_ID)
        self.assertEqual(dlg.result, 'play')
        self.assertTrue(dlg.closed)
        self.assertTrue(dlg._stop.is_set())

    def test_cancel_button_cancels(self):
        dlg = self._dialog()
        dlg.onClick(up_next.CANCEL_ID)
        self.assertEqual(dlg.result, 'cancel')
        self.assertTrue(dlg.closed)

    def test_back_cancels(self):
        dlg = self._dialog()
        action = MagicMock()
        action.getId.return_value = 10  # ACTION_PREVIOUS_MENU
        dlg.onAction(action)
        self.assertEqual(dlg.result, 'cancel')
        self.assertTrue(dlg.closed)

    def test_season_episode_label(self):
        self.assertEqual(
            up_next._season_episode_label({'season': 2, 'index': 5}),
            'S2 - E5')
        self.assertEqual(up_next._season_episode_label({}), '')


if __name__ == '__main__':
    unittest.main()
