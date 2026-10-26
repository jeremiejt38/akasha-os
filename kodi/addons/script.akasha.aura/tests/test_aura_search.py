"""Unit tests for aura_search.py search helpers (B8).

Same stub pattern as test_up_next.py: xbmc/xbmcgui are replaced before
import; the search window is instantiated against the fake dialog base.
Only the pure helpers (genre matching, suggestions, recent clearing)
are exercised -- no GUI calls.
"""

import os
import sys
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
        self.items = []

    def addItem(self, li):
        self.items.append(li)

    def reset(self):
        self.items = []

    def setLabel(self, label):
        self.label = label

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeListItem:
    def __init__(self, label='', label2=''):
        self._label = label
        self._label2 = label2
        self._props = {}

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeWindowXMLDialog:
    def __init__(self, *args, **kwargs):
        self._props = {}
        self._controls = {}
        self.closed = False
        self.focused = -1
        self.action_dispatched = []

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')

    def getControl(self, cid):
        if cid not in self._controls:
            self._controls[cid] = FakeControl(cid)
        return self._controls[cid]

    def getFocusId(self):
        return self.focused

    def setFocusId(self, cid):
        self.focused = cid

    def onAction(self, action):
        self.action_dispatched.append(action.getId())

    def close(self):
        self.closed = True


def _install_stubs():
    xbmc = _StubModule('xbmc')
    xbmc.LOGWARNING = 1
    xbmc.LOGERROR = 3
    gui = _StubModule('xbmcgui')
    gui.WindowXMLDialog = FakeWindowXMLDialog
    gui.ListItem = FakeListItem
    sys.modules['xbmc'] = xbmc
    sys.modules['xbmcgui'] = gui


_install_stubs()

import aura_search


def _window():
    win = aura_search.AuraSearchWindow('AuraSearch.xml', '.', 'Default', '1080i')
    win.sections = [{'key': '1', 'title': 'Films'},
                    {'key': '2', 'title': 'Series'}]
    return win


class TestSearchGenres(unittest.TestCase):
    def test_genre_matches_filtered_by_query(self):
        win = _window()
        win.client = MagicMock()
        win.client.section_genres.side_effect = lambda k: {
            '1': ['Action', 'Comedy'], '2': ['Action', 'Drama']}[k]
        win.query = 'act'
        genres = win._search_genres()
        self.assertEqual([g['name'] for g in genres], ['Action', 'Action'])
        self.assertTrue(all(g['_genre'] for g in genres))
        self.assertEqual(genres[0]['section_title'], 'Films')

    def test_genre_directories_fetched_once(self):
        win = _window()
        win.client = MagicMock()
        win.client.section_genres.return_value = ['Action']
        win.query = 'a'
        win._search_genres()
        win._search_genres()
        self.assertEqual(win.client.section_genres.call_count, 2)

    def test_no_client_returns_empty(self):
        win = _window()
        win.client = None
        win.query = 'a'
        self.assertEqual(win._search_genres(), [])

    def test_connector_payload_parsed(self):
        win = _window()
        win.client = MagicMock()
        win.client.section_genres.return_value = {
            'MediaContainer': {'Directory': [{'title': 'Horreur'}]}}
        win.query = 'hor'
        genres = win._search_genres()
        self.assertEqual([g['name'] for g in genres], ['Horreur', 'Horreur'])


class TestSuggestions(unittest.TestCase):
    def test_suggestions_from_discover_hubs(self):
        win = _window()
        win.client = MagicMock()
        win.client.discover_hubs.return_value = [
            {'title': 'Hub1', 'items': [{'title': 'A'}, {'title': 'B'}]},
            {'title': 'Hub2', 'items': [{'title': 'C'}]},
        ]
        self.assertEqual([i['title'] for i in win._suggestions()],
                         ['A', 'B', 'C'])

    def test_suggestions_without_endpoint(self):
        win = _window()
        win.client = MagicMock(spec=[])
        self.assertEqual(win._suggestions(), [])


class TestClearHistory(unittest.TestCase):
    def test_clear_row_appended_and_clickable(self):
        win = _window()
        win.recent = ['matrix', 'alien']
        win._render_recent()
        lst = win.getControl(aura_search.RECENT_LIST_ID)
        self.assertEqual(len(lst.items), 3)
        self.assertEqual(lst.items[-1].getProperty('clear'), '1')

        # Clicking the clear row empties the history.
        class _Pos:
            def getSelectedPosition(self):
                return 2
        lst.getSelectedPosition = _Pos().getSelectedPosition
        win.onClick(aura_search.RECENT_LIST_ID)
        self.assertEqual(win.recent, [])

    def test_recent_click_selects_query(self):
        win = _window()
        win.recent = ['matrix']
        win._render_recent()
        lst = win.getControl(aura_search.RECENT_LIST_ID)
        lst.getSelectedPosition = lambda: 0
        win.client = None
        win.onClick(aura_search.RECENT_LIST_ID)
        self.assertEqual(win.query, 'matrix')


class _Action:
    def __init__(self, aid):
        self._id = aid

    def getId(self):
        return self._id


class TestKeyboardRightEdge(unittest.TestCase):
    """Regression: MOVE_RIGHT on the keys panel with an empty query used
    to jump to the suggestions grid from ANY key, so first letters past
    column 0 ('b'...) were unreachable. Only the last column should
    leave the keyboard."""

    def test_mid_row_right_moves_within_grid(self):
        win = _window()
        win.query = ''
        win.focused = aura_search.KEYS_PANEL_ID
        win.getControl(aura_search.KEYS_PANEL_ID).getSelectedPosition = \
            lambda: 0  # 'a', column 0
        win.onAction(_Action(2))
        self.assertNotEqual(win.focused, aura_search.SUGGEST_PANEL_ID)
        self.assertIn(2, win.action_dispatched)  # delegated to Kodi

    def test_last_column_right_jumps_to_suggestions(self):
        win = _window()
        win.query = ''
        win.focused = aura_search.KEYS_PANEL_ID
        win.getControl(aura_search.KEYS_PANEL_ID).getSelectedPosition = \
            lambda: 5  # 'f', last column
        win.onAction(_Action(2))
        self.assertEqual(win.focused, aura_search.SUGGEST_PANEL_ID)
        self.assertNotIn(2, win.action_dispatched)

    def test_right_with_query_untouched(self):
        win = _window()
        win.query = 'b'
        win.focused = aura_search.KEYS_PANEL_ID
        win.getControl(aura_search.KEYS_PANEL_ID).getSelectedPosition = \
            lambda: 5
        win.onAction(_Action(2))
        self.assertNotEqual(win.focused, aura_search.SUGGEST_PANEL_ID)
        self.assertIn(2, win.action_dispatched)


if __name__ == '__main__':
    unittest.main()
