"""Unit tests for AuraWindow's Jeux helpers (E8/E11/E13).

Same stub pattern as test_divert_state.py: xbmc/xbmcaddon/xbmcgui are
replaced before importing aura_window, and the window is built with
__new__ so only the pure helper paths under test run.
"""

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


class FakeControl:
    def __init__(self, cid):
        self._cid = cid
        self.label = ''
        self.items = []

    def addItem(self, li):
        self.items.append(li)

    def addItems(self, items):
        self.items.extend(items)

    def reset(self):
        self.items = []

    def setLabel(self, label):
        self.label = label

    def getSelectedPosition(self):
        return 0

    def size(self):
        return len(self.items)

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

    def setFocus(self, control):
        self.focused = getattr(control, '_cid', control)

    def onAction(self, action):
        self.action_dispatched.append(action.getId())

    def close(self):
        self.closed = True


class _FakeAddon:
    def __init__(self, *args):
        self._settings = {}

    def getAddonInfo(self, key):
        return '/tmp/fake-addon'

    def getLocalizedString(self, msgid):
        return ''

    def getSetting(self, key):
        return self._settings.get(key, '')

    def setSetting(self, key, value):
        self._settings[key] = value


xbmc = _StubModule('xbmc')
xbmc.LOGWARNING = 1
xbmc.LOGERROR = 3
xbmcaddon = _StubModule('xbmcaddon')
xbmcaddon.Addon = _FakeAddon
xbmcgui = _StubModule('xbmcgui')
for _klass in ('WindowXMLDialog', 'WindowXML', 'Window'):
    setattr(xbmcgui, _klass, FakeWindowXMLDialog)
xbmcgui.ListItem = FakeListItem
xbmcvfs = _StubModule('xbmcvfs')

sys.modules['xbmc'] = xbmc
sys.modules['xbmcaddon'] = xbmcaddon
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcvfs'] = xbmcvfs

import aura_window  # noqa: E402
import sunshine_client  # noqa: E402


def _live(key, addon):
    """In tests the fresh-Addon indirection reads the fake directly."""
    return addon.getSetting(key)


def _make_window(settings=None):
    w = aura_window.AuraWindow.__new__(aura_window.AuraWindow)
    FakeWindowXMLDialog.__init__(w)
    w.addon = _FakeAddon()
    w.addon._settings.update(settings or {})
    w._games = [
        {'label': 'Steam Link', 'action': 'RunAddon(plugin.program.steamlink)'},
        {'label': 'Moonlight', 'action': 'RunAddon(plugin.program.moonlight-qt)'},
        {'label': 'Cloud Gaming', 'action': 'RunAddon(script.cloud.gaming)'},
    ]
    w._other_games = [w._games[2]]
    w._visible_games = list(w._other_games)
    w._sunshine_cache = None
    w._steam_cache = None
    return w


class TestCloudGamesPreference(unittest.TestCase):
    def test_no_preference_keeps_static_shortcuts(self):
        w = _make_window()
        with patch.object(aura_window, '_live_addon_setting', _live):
            self.assertEqual(w._visible_other_games(), w._other_games)

    def test_preference_surfaces_picked_cloud_services(self):
        w = _make_window(
            {'quickstart.cloud_gaming_services':
             'GeForce NOW,Xbox Cloud Gaming'})
        with patch.object(aura_window, '_live_addon_setting', _live):
            games = w._visible_other_games()
        self.assertEqual([g['label'] for g in games],
                         ['GeForce NOW', 'Xbox Cloud Gaming'])
        self.assertTrue(all(g['action'] == 'RunAddon(script.cloud.gaming)'
                            for g in games))

    def test_dedicated_names_stay_on_their_subtabs(self):
        w = _make_window(
            {'quickstart.cloud_gaming_services':
             'Steam Link,Moonlight,Amazon Luna'})
        with patch.object(aura_window, '_live_addon_setting', _live):
            games = w._visible_other_games()
        self.assertEqual([g['label'] for g in games], ['Amazon Luna'])

    def test_default_subtab_follows_preference(self):
        w = _make_window()
        with patch.object(aura_window, '_live_addon_setting', _live):
            self.assertEqual(w._default_jeux_subtab(),
                             aura_window.JEUX_SUBTAB_STEAMLINK)
        w.addon._settings['quickstart.cloud_gaming_services'] = 'Moonlight'
        with patch.object(aura_window, '_live_addon_setting', _live):
            self.assertEqual(w._default_jeux_subtab(),
                             aura_window.JEUX_SUBTAB_MOONLIGHT)
        w.addon._settings['quickstart.cloud_gaming_services'] = 'Boosteroid'
        with patch.object(aura_window, '_live_addon_setting', _live):
            self.assertEqual(w._default_jeux_subtab(),
                             aura_window.JEUX_SUBTAB_OTHERS)


class TestSunshineFallback(unittest.TestCase):
    def test_candidates_dedupe_primary_and_fallbacks(self):
        w = _make_window({
            'sunshine.server_url': 'https://10.20.0.4:47990',
            'sunshine.fallback_urls':
                'https://192.168.1.100:47990, https://10.20.0.4:47990',
        })
        with patch.object(aura_window, '_live_addon_setting', _live):
            urls = w._sunshine_candidates()
        self.assertEqual(urls, ['https://10.20.0.4:47990',
                                'https://192.168.1.100:47990'])

    def test_unconfigured_when_no_url_or_credentials(self):
        w = _make_window()
        with patch.object(aura_window, '_live_addon_setting', _live):
            state, apps = w._sunshine_apps()
        self.assertEqual(state, 'unconfigured')
        self.assertEqual(apps, [])

    def test_fallback_host_used_when_primary_fails(self):
        w = _make_window({
            'sunshine.server_url': 'https://dead:47990',
            'sunshine.fallback_urls': 'https://alive:47990',
            'sunshine.username': 'u',
            'sunshine.password': 'p',
        })
        calls = []

        def fake_client(url, user, pwd, timeout=5):
            calls.append(url)
            client = MagicMock()
            if url == 'https://dead:47990':
                client.apps.side_effect = sunshine_client.SunshineAPIError('down')
            else:
                client.apps.return_value = [{'name': 'Desktop',
                                             'box_art_url': 'x'}]
            return client

        with patch.object(aura_window, '_live_addon_setting', _live), \
                patch.object(sunshine_client, 'SunshineClient', fake_client):
            state, apps = w._sunshine_apps()
        self.assertEqual(calls, ['https://dead:47990', 'https://alive:47990'])
        self.assertEqual(state, 'ok')
        self.assertEqual(apps[0]['name'], 'Desktop')

    def test_all_hosts_down_reports_error_and_caches(self):
        w = _make_window({
            'sunshine.server_url': 'https://dead:47990',
            'sunshine.username': 'u',
            'sunshine.password': 'p',
        })
        client = MagicMock()
        client.apps.side_effect = sunshine_client.SunshineAPIError('down')
        with patch.object(aura_window, '_live_addon_setting', _live), \
                patch.object(sunshine_client, 'SunshineClient',
                             return_value=client):
            state, _apps = w._sunshine_apps()
            self.assertEqual(state, 'error')
            w._sunshine_apps()
        # Second call served by the error cache -- no new API hit.
        self.assertEqual(client.apps.call_count, 1)


class TestSearchGames(unittest.TestCase):
    def test_local_shortcut_and_catalog_hits_merged(self):
        w = _make_window()
        w._steam_cache = {'ts': 0, 'games': []}
        with patch.object(aura_window, '_live_addon_setting', _live), \
                patch.object(w, '_steam_catalog', return_value=[
                    {'name': 'Half-Life 2', 'box_art_url': 'b'}]), \
                patch.object(w, '_sunshine_apps', return_value=(
                    'ok', [{'name': 'Steam Big Picture',
                            'box_art_url': 's'}])):
            hits = w._game_search_hits('steam')
        titles = [h['title'] for h in hits]
        self.assertIn('Steam Link', titles)
        self.assertIn('Steam Big Picture', titles)
        self.assertTrue(all(h['_game'] for h in hits))

    def test_dead_services_contribute_no_hits(self):
        w = _make_window()
        with patch.object(w, '_steam_catalog', return_value=[]), \
                patch.object(w, '_sunshine_apps', return_value=('error', [])):
            hits = w._game_search_hits('cloud')
        self.assertEqual([h['title'] for h in hits], ['Cloud Gaming'])

    def test_unified_search_lists_catalog_entries(self):
        w = _make_window()
        with patch.object(w, '_steam_catalog', return_value=[
                {'name': 'Half-Life 2', 'box_art_url': 'b'}]), \
                patch.object(w, '_sunshine_apps', return_value=('ok', [])):
            results = w._search_games('half')
        self.assertEqual([label for label, _cb in results], ['Half-Life 2'])

    def test_empty_query_returns_nothing(self):
        w = _make_window()
        self.assertEqual(w._game_search_hits('  '), [])


if __name__ == '__main__':
    unittest.main()
