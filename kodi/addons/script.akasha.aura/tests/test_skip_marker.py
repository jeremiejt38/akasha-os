"""Unit tests for skip_marker.py (B2 Skip Intro / Skip Credits).

Same stub pattern as the other OSD tests. Shared-module attributes
(xbmc.Player, osd_menu helpers) are patched per test via patch.object
so nothing leaks into the test files that run after this one -- the
xbmc stub module object is shared across the whole pytest run.
"""

import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        mock = MagicMock(name=name)
        setattr(self, name, mock)
        return mock


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
            self._controls[cid] = MagicMock()
        return self._controls[cid]

    def setFocusId(self, cid):
        self._focus = cid

    def close(self):
        self.closed = True


class FakeHomeWindow:
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
xbmcgui.WindowXMLDialog = FakeWindowXMLDialog
xbmcgui.Window = lambda *args: _home

sys.modules.setdefault('xbmc', xbmc)
sys.modules.setdefault('xbmcaddon', xbmcaddon)
sys.modules.setdefault('xbmcgui', xbmcgui)
sys.modules.setdefault('xbmcvfs', _StubModule('xbmcvfs'))

import osd_menu  # noqa: E402
import skip_marker  # noqa: E402

# Module-local pin: skip_marker's own `_home` helper, safe to rebind.
skip_marker._home = lambda: _home

_fake_player = MagicMock()

_MARKERS = [
    {'type': 'intro', 'start_ms': 5000, 'end_ms': 90000},
    {'type': 'credits', 'start_ms': 2400000, 'end_ms': 2520000},
]


def _update(pos_s=10.0, markers=_MARKERS, playing=True):
    """update_active_marker() with the player + marker source patched."""
    _fake_player.isPlayingVideo.return_value = playing
    _fake_player.getTime.return_value = pos_s
    with patch.object(skip_marker.xbmc, 'Player', lambda *a: _fake_player), \
            patch.object(skip_marker.osd_menu, '_current_markers',
                         lambda: markers):
        return skip_marker.update_active_marker()


class ActiveMarkerTests(unittest.TestCase):

    def test_position_inside_marker_returns_it(self):
        self.assertIs(
            skip_marker.active_marker(_MARKERS, 10000), _MARKERS[0])
        self.assertIs(
            skip_marker.active_marker(_MARKERS, 2450000), _MARKERS[1])

    def test_boundaries(self):
        self.assertIs(skip_marker.active_marker(_MARKERS, 5000), _MARKERS[0])
        self.assertIsNone(skip_marker.active_marker(_MARKERS, 90000))

    def test_outside_and_empty(self):
        self.assertIsNone(skip_marker.active_marker(_MARKERS, 100000))
        self.assertIsNone(skip_marker.active_marker([], 10000))
        self.assertIsNone(skip_marker.active_marker(None, 10000))

    def test_malformed_entries_skipped(self):
        bad = [{'foo': 1}, {'type': 'intro', 'start_ms': 'x', 'end_ms': 5}]
        self.assertIsNone(skip_marker.active_marker(bad, 10))


class UpdateActiveMarkerTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _fake_player.reset_mock(return_value=True, side_effect=True)

    def test_publishes_active_marker_json(self):
        marker = _update(pos_s=10.0)
        self.assertEqual(marker['type'], 'intro')
        stored = json.loads(_home.getProperty(skip_marker.PROP_ACTIVE))
        self.assertEqual(stored['end_ms'], 90000)

    def test_clears_prop_outside_marker(self):
        self.assertIsNone(_update(pos_s=100.0))
        self.assertEqual(_home.getProperty(skip_marker.PROP_ACTIVE), '')

    def test_clears_prop_when_not_playing(self):
        self.assertIsNone(_update(playing=False))
        self.assertEqual(_home.getProperty(skip_marker.PROP_ACTIVE), '')

    def test_no_markers_returns_none(self):
        self.assertIsNone(_update(markers=[]))


class StoreMarkersTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()

    def _store(self, client, item):
        with patch.object(osd_menu, '_home', lambda: _home):
            osd_menu.store_markers(client, item)

    def test_fetches_and_keys_by_rating_key(self):
        client = MagicMock()
        client.item_markers.return_value = _MARKERS
        self._store(client, {'rating_key': '42'})
        stored = json.loads(_home.getProperty(osd_menu.PROP_MARKERS))
        self.assertEqual(stored['42'], _MARKERS)
        client.item_markers.assert_called_once_with('42')

    def test_client_without_marker_support_stores_empty(self):
        self._store(object(), {'rating_key': '42'})
        self.assertEqual(
            json.loads(_home.getProperty(osd_menu.PROP_MARKERS)), {})

    def test_fetch_failure_stores_empty(self):
        client = MagicMock()
        client.item_markers.side_effect = RuntimeError('boom')
        self._store(client, {'rating_key': '42'})
        self.assertEqual(
            json.loads(_home.getProperty(osd_menu.PROP_MARKERS)), {})


class DialogTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _fake_player.reset_mock(return_value=True, side_effect=True)
        _home.setProperty(skip_marker.PROP_ACTIVE,
                          json.dumps(_MARKERS[0]))

    def _dialog(self):
        """Instance-level stubs: AuraSkipMarkerWindow's base class is
        whichever WindowXMLDialog fake happened to be in sys.modules at
        import, so methods are bound on the instance to stay
        deterministic. The marker watcher thread is also neutralised --
        the tests drive _dismiss/onClick directly."""
        dlg = skip_marker.AuraSkipMarkerWindow.__new__(
            skip_marker.AuraSkipMarkerWindow)
        dlg._controls = {}
        dlg.closed = False
        dlg._focus = None
        dlg.getControl = lambda cid: dlg._controls.setdefault(
            cid, MagicMock())
        dlg.setFocusId = lambda cid: setattr(dlg, '_focus', cid)
        dlg.close = lambda: setattr(dlg, 'closed', True)
        return dlg

    def test_init_labels_and_focuses_button(self):
        dlg = self._dialog()
        with patch.object(skip_marker.threading, 'Thread'):
            dlg.onInit()
        label = dlg.getControl(skip_marker.SKIP_BUTTON_ID).setLabel \
            .call_args[0][0]
        self.assertTrue(label)  # localized Skip Intro
        self.assertEqual(dlg._focus, skip_marker.SKIP_BUTTON_ID)
        self.assertEqual(dlg._end_ms, 90000)

    def test_init_closes_without_active_marker(self):
        _home.setProperty(skip_marker.PROP_ACTIVE, '')
        dlg = self._dialog()
        with patch.object(skip_marker.threading, 'Thread'):
            dlg.onInit()
        self.assertTrue(dlg.closed)

    def test_click_seeks_to_marker_end(self):
        dlg = self._dialog()
        with patch.object(skip_marker.threading, 'Thread'):
            dlg.onInit()
        with patch.object(skip_marker.xbmc, 'Player',
                          lambda *a: _fake_player):
            dlg.onClick(skip_marker.SKIP_BUTTON_ID)
        self.assertTrue(dlg.closed)
        _fake_player.seekTime.assert_called_once_with(90.0)
        self.assertEqual(_home.getProperty(skip_marker.PROP_ACTIVE), '')

    def test_back_dismisses(self):
        dlg = self._dialog()
        with patch.object(skip_marker.threading, 'Thread'):
            dlg.onInit()
        action = MagicMock()
        action.getId.return_value = osd_menu._back_ids()[0]
        dlg.onAction(action)
        self.assertTrue(dlg.closed)

    def test_label_id_per_marker_type(self):
        self.assertEqual(skip_marker._marker_label_id('intro'), 33568)
        self.assertEqual(skip_marker._marker_label_id('credits'), 33569)
        self.assertEqual(skip_marker._marker_label_id('commercial'), 33570)


if __name__ == '__main__':
    unittest.main()
