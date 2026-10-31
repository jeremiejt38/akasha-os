"""Unit tests for AuraWindow's DivertState machinery (B17).

aura_window imports xbmc/xbmcaddon/xbmcgui (dialog classes), so tests
stub them out before importing -- same approach as test_aura_detail.py,
extended with a permissive module type since aura_window pulls in the
whole lib. The window itself is never shown: tests exercise the pure
state-decision paths (_apply_reco_state, _state_for_error,
_apply_grid_empty_state, _set_divert_state, _apply_browse_restate and
the action thunks) against a fake control surface.
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))


class _StubModule(types.ModuleType):
    """Module stand-in: any attribute not explicitly set is a MagicMock."""

    def __getattr__(self, name):
        mock = MagicMock(name=name)
        setattr(self, name, mock)
        return mock


class FakeControl:
    """Records labels and exposes a size() for list controls."""

    def __init__(self, cid):
        self._cid = cid
        self.label = ''
        self._size = 0

    def setLabel(self, label):
        self.label = label

    def reset(self):
        self._size = 0

    def addItem(self, item):
        self._size += 1

    def size(self):
        return self._size

    def getSelectedPosition(self):
        return 0

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeWindowXMLDialog:
    """Property/control surface standing in for Kodi's window base."""

    def __init__(self, *args, **kwargs):
        self._props = {}
        self._controls = {}
        self._focus = None

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')

    def getControl(self, cid):
        if cid not in self._controls:
            self._controls[cid] = FakeControl(cid)
        return self._controls[cid]

    def getFocusId(self):
        return self._focus if self._focus is not None else -1

    def setFocusId(self, cid):
        self._focus = cid

    def setFocus(self, control):
        self._focus = getattr(control, '_cid', control)


class _FakeAddon:
    def getAddonInfo(self, key):
        return '/tmp/fake-addon'

    def getLocalizedString(self, msgid):
        return ''

    def getSetting(self, key):
        return ''


xbmc = _StubModule('xbmc')
xbmcaddon = _StubModule('xbmcaddon')
xbmcaddon.Addon = _FakeAddon
xbmcgui = _StubModule('xbmcgui')
for _klass in ('WindowXMLDialog', 'WindowXML', 'Window'):
    setattr(xbmcgui, _klass, FakeWindowXMLDialog)
xbmcgui.ListItem = MagicMock
xbmcvfs = _StubModule('xbmcvfs')

sys.modules['xbmc'] = xbmc
sys.modules['xbmcaddon'] = xbmcaddon
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcvfs'] = xbmcvfs

import aura_window  # noqa: E402
import connector_client  # noqa: E402
import i18n  # noqa: E402
import plex_client  # noqa: E402

TITLE_ID = aura_window.DIVERT_STATE_TITLE_ID
BUTTON_ID = aura_window.DIVERT_STATE_BUTTON_ID
SIDEBAR_ID = aura_window.DIVERT_SIDEBAR_ID


class _FakePaged:
    def __init__(self, items):
        self.items = items


def _row(items, error=None):
    return {'title': 'row', 'paged': _FakePaged(items), 'error': error}


def _make_window():
    """Bare AuraWindow with just the fields the state paths touch."""
    w = aura_window.AuraWindow.__new__(aura_window.AuraWindow)
    FakeWindowXMLDialog.__init__(w)
    w._plex_client = MagicMock()
    w._connector_client = None
    w._divert_sections = [
        {'key': '1', 'title': 'Films', 'type': 'movie'}]
    w._hub_rows = []
    w._hub_offset = 0
    w._reco_rows = {}
    w._reco_placeholder_counts = {}
    w._divert_items = []
    w._divert_paged = None
    w._divert_view = 'home'
    w._divert_library_tab = 0
    w._home_tab = 0
    w._divert_sort = None
    w._divert_filter_genre = None
    w._divert_filter_unwatched = None
    w._divert_filters = {}
    w._divert_search_query = ''
    w._divert_state = None
    w._divert_state_action = None
    w._slot_promo = set()
    return w


class RecoStateTests(unittest.TestCase):

    def test_no_client_shows_config_state(self):
        w = _make_window()
        w._plex_client = None
        w._divert_sections = []
        w._hub_rows = [_row([])]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'config')
        self.assertEqual(w._divert_state_action, w._open_settings_menu)

    def test_all_rows_offline_shows_offline_state(self):
        w = _make_window()
        fatal = plex_client.PlexOfflineError('down')
        w._hub_rows = [_row([], error=fatal)]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'offline')
        self.assertEqual(w._hub_rows, [])
        self.assertEqual(w._controls[TITLE_ID].label, i18n.tr(33550))
        self.assertEqual(w._controls[BUTTON_ID].label, i18n.tr(33552))
        self.assertEqual(w._focus, BUTTON_ID)

    def test_all_rows_errored_shows_error_state(self):
        w = _make_window()
        w._hub_rows = [
            _row([], error=plex_client.PlexAPIError('500')),
            _row([], error=ValueError('x'))]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'error')

    def test_partial_failure_keeps_rows_and_no_state(self):
        w = _make_window()
        w._hub_rows = [
            _row([{'a': 1}]),
            _row([], error=plex_client.PlexAPIError('500'))]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], '')
        self.assertEqual(len(w._hub_rows), 2)

    def test_error_rows_plus_silent_empties_still_state(self):
        w = _make_window()
        err = connector_client.ConnectorOfflineError('down')
        w._plex_client = None
        w._connector_client = MagicMock()
        w._hub_rows = [_row([], error=err), _row([], error=err), _row([])]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'offline')

    def test_empty_hub_shows_empty_state(self):
        w = _make_window()
        w._hub_rows = []
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'empty')
        self.assertEqual(w._controls[BUTTON_ID].label, i18n.tr(33552))

    def test_retry_reloads_divertissement_when_no_sections(self):
        w = _make_window()
        w._connector_client = MagicMock()
        w._divert_sections = []
        w._hub_rows = [
            _row([], error=connector_client.ConnectorOfflineError('d'))]
        calls = []
        w._load_divertissement = lambda: calls.append('divert')
        w._restore_divert_view = lambda focus=False: calls.append(
            ('restore', focus))
        w._apply_reco_state(None)
        w._divert_state_action()
        self.assertIn('divert', calls)
        self.assertEqual(calls[-1], ('restore', False))


class GridStateTests(unittest.TestCase):

    def setUp(self):
        self.section = {'key': '1', 'title': 'Films', 'type': 'movie'}

    def test_offline_grid_error_shows_offline_state(self):
        w = _make_window()
        calls = []
        w._load_divert_section_items = lambda s: calls.append(s)
        w._state_for_error(
            plex_client.PlexOfflineError('down'),
            lambda: w._load_divert_section_items(self.section))
        self.assertEqual(w._props['DivertState'], 'offline')
        w._divert_state_action()
        self.assertEqual(calls, [self.section])

    def test_api_error_shows_generic_error_state(self):
        w = _make_window()
        w._state_for_error(plex_client.PlexAPIError('500'), lambda: None)
        self.assertEqual(w._props['DivertState'], 'error')
        self.assertEqual(w._controls[BUTTON_ID].label, i18n.tr(33552))

    def test_filtered_empty_offers_clear_filters(self):
        w = _make_window()
        w._divert_filter_genre = 'Drame'
        calls = []
        w._load_divert_section_items = lambda s: calls.append(s)
        w._apply_grid_empty_state(self.section)
        self.assertEqual(w._props['DivertState'], 'empty')
        self.assertEqual(w._controls[TITLE_ID].label, i18n.tr(33556))
        self.assertEqual(w._controls[BUTTON_ID].label, i18n.tr(33557))
        w._divert_state_action()
        self.assertIsNone(w._divert_filter_genre)
        self.assertEqual(calls, [self.section])

    def test_unfiltered_empty_offers_back_to_sidebar(self):
        w = _make_window()
        w._apply_grid_empty_state(self.section)
        self.assertEqual(w._controls[TITLE_ID].label, i18n.tr(33555))
        self.assertEqual(w._controls[BUTTON_ID].label, i18n.tr(33020))
        w._divert_state_action()
        self.assertEqual(w._focus, SIDEBAR_ID)

    def test_restate_keeps_error_over_empty(self):
        w = _make_window()
        w._divert_state = 'error'
        w._apply_browse_restate(self.section)
        self.assertEqual(w._divert_state, 'error')

    def test_restate_clears_state_when_items_present(self):
        w = _make_window()
        w._divert_items = [{'x': 1}]
        w._divert_state = 'empty'
        w._apply_browse_restate(self.section)
        self.assertIsNone(w._divert_state)
        self.assertEqual(w._props['DivertState'], '')

    def test_clear_resets_labels_and_action(self):
        w = _make_window()
        w._set_divert_state('error', 't', 'm', 'a', lambda: None)
        w._set_divert_state(None)
        self.assertIsNone(w._divert_state)
        self.assertIsNone(w._divert_state_action)
        self.assertEqual(w._props['DivertState'], '')
        self.assertEqual(w._controls[TITLE_ID].label, '')
        self.assertEqual(w._controls[BUTTON_ID].label, '')


class EmptyHubRowsTests(unittest.TestCase):
    """A section whose hubs are all empty (e.g. a music library with no
    scrobbles) must render the empty state, not the video-centric legacy
    rows, and must not keep the previous view's hero."""

    def _hub(self, items, key=''):
        return {'title': 'hub', 'key': key, 'identifier': 'h',
                'context': '', 'type': '', 'style': 'shelf',
                'more': False, 'items': items}

    def test_empty_hubs_return_empty_not_fallback(self):
        w = _make_window()
        w._plex_client.section_hubs = lambda key: [self._hub([])]
        rows, fatal = w._reco_hub_rows({'key': '6', 'type': 'artist'})
        self.assertEqual(rows, [])
        self.assertIsNone(fatal)

    def test_no_hubs_still_falls_back_to_legacy(self):
        w = _make_window()
        w._plex_client.section_hubs = lambda key: []
        rows, fatal = w._reco_hub_rows({'key': '6', 'type': 'artist'})
        self.assertIsNone(rows)
        self.assertIsNone(fatal)

    def test_legacy_rows_drop_empty_pages(self):
        w = _make_window()
        w._plex_client = None
        w._connector_client = MagicMock()
        w._reco_fetch_on_deck_page = lambda s, o, l: ([], 0)
        w._reco_fetch_recently_added_page = lambda s, o, l: ([], 0)
        w._reco_fetch_recent_releases_page = lambda s, o, l: ([], 0)
        w._reco_get_first_video_section = lambda: {'key': '1', 'title': 'F'}
        self.assertEqual(w._reco_legacy_rows(None), [])

    def test_hero_cleared_when_reload_has_no_items(self):
        import threading
        w = _make_window()
        w._hero_fanart_timer = None
        w._hero_fanart_lock = threading.Lock()
        w._hero_fanart_current = 'fanart.jpg'
        w._props['AuraHeroTitle'] = 'Stale Title'
        w._props['AuraHeroFanart'] = 'fanart.jpg'
        w._update_hero(clear_if_empty=True)
        self.assertEqual(w._props['AuraHeroTitle'], '')
        self.assertEqual(w._props['AuraHeroFanart'], '')
        self.assertIsNone(w._hero_fanart_current)

    def test_hero_kept_when_focus_leaves_rows(self):
        import threading
        w = _make_window()
        w._hero_fanart_timer = None
        w._hero_fanart_lock = threading.Lock()
        w._hero_fanart_current = 'fanart.jpg'
        w._props['AuraHeroTitle'] = 'Kept Title'
        w._update_hero()  # focus-time call: hero must not blank
        self.assertEqual(w._props['AuraHeroTitle'], 'Kept Title')


PROMO_IDS = aura_window.RECO_PROMO_IDS
LIST_IDS = aura_window.RECO_LIST_IDS


class TrendingPromoTests(unittest.TestCase):
    """Plex's Tendances tab ends with a full-width promo card ("Find What
    To Watch, Anywhere!"). It binds as a synthetic trailing hub row
    rendered by a focusable button per slot -- these cover the binding,
    the effective-id resolution and the nav bookkeeping."""

    def _promo_window(self, rows):
        import threading
        w = _make_window()
        w._ui_lock = threading.RLock()
        w._hub_rows = rows
        w._hub_offset = 0
        # _rebind_reco_slots tails out to nav/label/pagination helpers not
        # under test here.
        w._drop_pending_appends = lambda *a: None
        w._sync_navigation = lambda: None
        w._render_reco_row_label = lambda *a, **k: None
        w._sync_placeholders = lambda *a, **k: 0
        return w

    def test_promo_row_binds_button_and_style_property(self):
        w = self._promo_window(
            [_row([{'a': 1}]), {'title': '', 'paged': None, 'promo': True}])
        w._rebind_reco_slots()
        self.assertEqual(w._props['AuraRowStyle1'], 'promo')
        self.assertEqual(w._slot_promo, {1})
        # The slot's lists stay empty -- the promo button renders the card.
        self.assertEqual(w._controls[LIST_IDS[1]].size(), 0)
        self.assertNotIn(LIST_IDS[1], w._reco_rows)
        self.assertNotIn(LIST_IDS[1] + 1, w._reco_rows)
        self.assertEqual(w._controls[5200].label, '')
        self.assertEqual(w._controls[5201].label, '')

    def test_promo_slot_effective_id_is_the_button(self):
        w = self._promo_window(
            [_row([{'a': 1}]), {'title': '', 'paged': None, 'promo': True}])
        w._rebind_reco_slots()
        self.assertEqual(w._reco_slot_list_id(1), PROMO_IDS[1])
        self.assertEqual(w._reco_slot_list_id(0), LIST_IDS[0])

    def test_bound_promo_counts_as_filled_for_nav(self):
        w = self._promo_window(
            [_row([{'a': 1}]), {'title': '', 'paged': None, 'promo': True}])
        w._rebind_reco_slots()
        self.assertTrue(w._reco_list_has_items(PROMO_IDS[1]))
        self.assertFalse(w._reco_list_has_items(PROMO_IDS[2]))

    def test_slot_index_maps_promo_button_ids(self):
        w = _make_window()
        for i, pid in enumerate(PROMO_IDS):
            self.assertEqual(w._reco_slot_index(pid), i)
        self.assertEqual(w._reco_slot_index(999999), -1)

    def test_rebind_without_promo_clears_slot_state(self):
        w = self._promo_window(
            [_row([{'a': 1}]), {'title': '', 'paged': None, 'promo': True}])
        w._rebind_reco_slots()
        w._hub_rows = [_row([{'a': 1}]), _row([{'b': 2}])]
        w._rebind_reco_slots()
        self.assertEqual(w._slot_promo, set())
        self.assertEqual(w._reco_slot_list_id(1), LIST_IDS[1])
        self.assertFalse(w._reco_list_has_items(PROMO_IDS[1]))

    def test_promo_not_appended_to_error_only_load(self):
        # The append guard requires at least one row with items -- a fully
        # errored Tendances load must not end on the promo card.
        w = _make_window()
        fatal = plex_client.PlexOfflineError('down')
        w._hub_rows = [_row([], error=fatal)]
        w._apply_reco_state(None)
        self.assertEqual(w._props['DivertState'], 'offline')
        self.assertEqual(w._hub_rows, [])


class RecoScrollFocusSlotTests(unittest.TestCase):
    """Scrolling the hub viewport resets the focused slot's list, which
    drops focus; slot lists are only <visible> while a reco control holds
    focus, so the deferred restore would hit an invisible control and
    Kodi would park on the top bar. _reco_scroll publishes AuraFocusSlot
    to force-render the anchor slot until the deferred SetFocus lands."""

    def _scroll_window(self, row_count=7):
        import threading
        w = _make_window()
        w._ui_lock = threading.RLock()
        w._hub_rows = [_row([{'i': i}]) for i in range(row_count)]
        w._hub_offset = 0
        w._drop_pending_appends = lambda *a: None
        w._sync_navigation = lambda: None
        w._render_reco_row_label = lambda *a, **k: None
        w._sync_placeholders = lambda *a, **k: 0
        w._clear_focus_slot_later = lambda *a, **k: None
        return w

    def test_scroll_down_publishes_last_slot_until_focus_lands(self):
        w = self._scroll_window()
        deferred = []
        w._defer_focus = lambda cid, delay=0.3: deferred.append(cid)
        self.assertTrue(w._reco_scroll(+1))
        self.assertEqual(w._props['AuraFocusSlot'],
                         str(len(LIST_IDS) - 1))
        self.assertEqual(deferred,
                         [w._reco_slot_list_id(len(LIST_IDS) - 1)])

    def test_scroll_up_publishes_first_slot(self):
        w = self._scroll_window()
        w._hub_offset = 2
        w._defer_focus = lambda cid, delay=0.3: None
        self.assertTrue(w._reco_scroll(-1))
        self.assertEqual(w._props['AuraFocusSlot'], '0')

    def test_no_scroll_when_already_at_edge_publishes_nothing(self):
        w = self._scroll_window()
        self.assertFalse(w._reco_scroll(-1))
        self.assertEqual(w._props.get('AuraFocusSlot', ''), '')

    def test_focus_slot_cleared_on_state_paths(self):
        w = _make_window()
        w._props['AuraFocusSlot'] = '4'
        w._hub_rows = [_row([], error=plex_client.PlexOfflineError('x'))]
        w._apply_reco_state(None)
        self.assertEqual(w._props['AuraFocusSlot'], '')


if __name__ == '__main__':
    unittest.main()
