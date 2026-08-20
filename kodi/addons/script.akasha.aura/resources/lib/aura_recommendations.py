"""Akasha Aura — Recommandations view (hero rows: Continuer a regarder / Ajoutes recemment).

Milestone 6 (see docs/aura/roadmap.md): tries akasha-os-connector first (using
the session token already established from the Divertissement tab, see
aura_window.py::_get_connector_client), falls back to direct Plex API access
(plex_client.py, already in production) if the connector is not configured or
the stored session is invalid. No login prompt here: a user reaching this
window is expected to already be authenticated (or intentionally not using
the connector), keeping this window's flow simple.

Milestone 9: each row loads incrementally (paged_list.PagedList) instead of
fetching everything upfront -- a first page eagerly, then more as the user
scrolls right -- and pages are cached on-device (local_cache.LocalCache) so
revisiting this window doesn't refetch over the network every time.
"""
import xbmc
import xbmcaddon
import xbmcgui

import connector_client
import divert_source
import local_cache
import paged_list
import plex_client

ON_DECK_FETCH_LIMIT = 50  # over-fetch before client-side section filtering

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

ROW_ON_DECK_LABEL_ID = 5100
ROW_ON_DECK_LIST_ID = 5110
ROW_RECENT_LABEL_ID = 5200
ROW_RECENT_LIST_ID = 5210
ROW_RELEASES_LABEL_ID = 5300
ROW_RELEASES_LIST_ID = 5310
STATUS_LABEL_ID = 5020

ROW_CACHE_TTL_SECONDS = 120


class AuraRecommendationsWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self._connector = None
        self._plex = None
        self._first_section = None
        self._cache = local_cache.open_addon_cache(self.addon)
        # {list_control_id: (row_title, PagedList)}
        self._rows = {}
        # Optional: set by the caller (AuraWindow) before doModal() to scope
        # every row to a single library instead of across all of them --
        # None means "Accueil" (global, plan 780ecf80 phase 3).
        self.section = None

    def onInit(self):
        try:
            self._connect()
            on_deck_title = 'Continuer a regarder'
            recent_title = 'Ajoutes recemment'
            if self.section:
                on_deck_title += ' dans {}'.format(self.section['title'])
                recent_title += ' dans {}'.format(self.section['title'])
            self._init_row(ROW_ON_DECK_LABEL_ID, ROW_ON_DECK_LIST_ID,
                            on_deck_title, self._fetch_on_deck_page)
            self._init_row(ROW_RECENT_LABEL_ID, ROW_RECENT_LIST_ID,
                            recent_title, self._fetch_recently_added_page)

            releases_title = 'Sorties recentes'
            releases_section = self.section or self._get_first_video_section()
            if releases_section:
                releases_title = 'Sorties recentes dans {}'.format(releases_section['title'])
            self._init_row(ROW_RELEASES_LABEL_ID, ROW_RELEASES_LIST_ID,
                            releases_title, self._fetch_recent_releases_page)

            # The XML's <defaultcontrol> is the back button (safe fallback if a
            # row fails to load); once rows are populated, focus the first
            # non-empty one so Left/Right immediately scrolls content.
            for list_control_id in (ROW_ON_DECK_LIST_ID, ROW_RECENT_LIST_ID, ROW_RELEASES_LIST_ID):
                row = self._rows.get(list_control_id)
                if row and row[2].items:
                    self.setFocus(self.getControl(list_control_id))
                    break
        except Exception as e:
            xbmc.log('Akasha Aura Recommendations: init error: {}'.format(e), xbmc.LOGERROR)

    def _connect(self):
        server_url = self.addon.getSetting('connector.server_url')
        stored_token = self.addon.getSetting('connector.session_token')
        if server_url and stored_token:
            client = connector_client.ConnectorClient(server_url, timeout=15)
            client.token = stored_token
            self._connector = client
            return

        plex_url = self.addon.getSetting('plex.server_url')
        plex_token = self.addon.getSetting('plex.token')
        if plex_url and plex_token:
            self._plex = plex_client.PlexClient(plex_url, plex_token, timeout=15)

    def _fetch_on_deck_page(self, offset, limit):
        key = local_cache.page_cache_key(
            'on-deck', self.section['key'] if self.section else 'home', offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, ROW_CACHE_TTL_SECONDS,
            lambda: self._fetch_on_deck_page_uncached(offset, limit))

    def _fetch_on_deck_page_uncached(self, offset, limit):
        # No dedicated "on-deck for this section" endpoint on the connector or
        # plex_client -- over-fetch the global on-deck list and filter
        # client-side by section_id (see divert_source.filter_by_section).
        # Only an approximation of the real total when scoped to a library
        # (Plex's totalSize covers every library), documented in
        # docs/aura/decisions.md.
        fetch_limit = ON_DECK_FETCH_LIMIT if self.section else limit
        fetch_offset = 0 if self.section else offset
        if self._connector:
            raw = self._connector.on_deck(limit=fetch_limit, offset=fetch_offset)
            items = divert_source.parse_metadata_list(raw, self._connector.image_url)
            total = divert_source.parse_total_size(raw)
        elif self._plex:
            items, total = self._plex.on_deck_with_total(limit=fetch_limit, offset=fetch_offset)
        else:
            return [], None
        if not self.section:
            return items, total
        filtered = divert_source.filter_by_section(items, self.section['key'])
        return filtered[offset:offset + limit], len(filtered)

    def _fetch_recently_added_page(self, offset, limit):
        # Home (self.section is None): globally recently added, across every
        # library. A specific library: that library's own recently-added
        # items (sorted by addedAt, same shape/endpoint as
        # aura_library.py's default sort) -- distinct from the "Sorties
        # recentes" row below, which sorts by release date instead.
        if self.section:
            return self._fetch_section_items_page(
                self.section, 'recently-added', 'addedAt:desc', offset, limit)
        key = local_cache.page_cache_key('recently-added', offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, ROW_CACHE_TTL_SECONDS,
            lambda: self._fetch_recently_added_page_uncached(offset, limit))

    def _fetch_recently_added_page_uncached(self, offset, limit):
        if self._connector:
            raw = self._connector.recently_added(limit=limit, offset=offset)
            items = divert_source.parse_metadata_list(raw, self._connector.image_url)
            return items, divert_source.parse_total_size(raw)
        if self._plex:
            return self._plex.recently_added_with_total(limit=limit, offset=offset)
        return [], None

    def _get_first_video_section(self):
        if self._first_section is not None:
            return self._first_section
        sections = []
        if self._connector:
            sections = divert_source.parse_sections(self._connector.sections())
        elif self._plex:
            sections = self._plex.video_sections()
        self._first_section = sections[0] if sections else False
        return self._first_section or None

    def _fetch_recent_releases_page(self, offset, limit):
        section = self.section or self._get_first_video_section()
        if not section:
            return [], None
        return self._fetch_section_items_page(
            section, 'recent-releases', 'originallyAvailableAt:desc', offset, limit)

    def _fetch_section_items_page(self, section, cache_label, sort, offset, limit):
        key = local_cache.page_cache_key(cache_label, section['key'], offset, limit)
        return local_cache.get_or_set_page(
            self._cache, key, ROW_CACHE_TTL_SECONDS,
            lambda: self._fetch_section_items_page_uncached(section, sort, offset, limit))

    def _fetch_section_items_page_uncached(self, section, sort, offset, limit):
        if self._connector:
            raw = self._connector.section_items(
                section['key'], sort=sort, limit=limit, offset=offset)
            items = divert_source.parse_metadata_list(raw, self._connector.image_url)
            return items, divert_source.parse_total_size(raw)
        if self._plex:
            return self._plex.section_items_with_total(
                section['key'], sort=sort, limit=limit, offset=offset)
        return [], None

    def _init_row(self, label_control_id, list_control_id, title, fetch_page_fn):
        paged = paged_list.PagedList(fetch_page_fn)
        error = None
        try:
            paged.load_initial()
        except (connector_client.ConnectorAPIError, plex_client.PlexAPIError) as e:
            error = e
        except Exception as e:  # defensive: never crash the window on a row failure
            error = e

        self._rows[list_control_id] = (label_control_id, title, paged)
        self._render_row_label(list_control_id, error)

        if error:
            xbmc.log('Akasha Aura Recommendations: {} failed: {}'.format(title, error),
                     xbmc.LOGWARNING)
            return

        try:
            lst = self.getControl(list_control_id)
            lst.reset()
            for item in paged.items:
                lst.addItem(_build_list_item(item))
        except Exception as e:
            xbmc.log('Akasha Aura Recommendations: render error for {}: {}'.format(title, e),
                     xbmc.LOGERROR)

    def _render_row_label(self, list_control_id, error=None):
        label_control_id, title, paged = self._rows[list_control_id]
        try:
            self.getControl(label_control_id).setLabel(
                '{} — erreur de chargement'.format(title) if error else
                '{} ({})'.format(title, _format_count(paged)))
        except RuntimeError:
            pass

    def _maybe_load_more(self, list_control_id):
        row = self._rows.get(list_control_id)
        if not row:
            return
        label_control_id, title, paged = row
        try:
            position = self.getControl(list_control_id).getSelectedPosition()
        except RuntimeError:
            return

        try:
            new_items = paged.maybe_load_more(position)
        except Exception as e:
            xbmc.log('Akasha Aura Recommendations: pagination fetch failed for {}: {}'
                     .format(title, e), xbmc.LOGWARNING)
            return
        if not new_items:
            return

        try:
            lst = self.getControl(list_control_id)
            lst.addItems([_build_list_item(item) for item in new_items])
        except Exception as e:
            xbmc.log('Akasha Aura Recommendations: append render error for {}: {}'
                     .format(title, e), xbmc.LOGERROR)
        self._render_row_label(list_control_id)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)
        if aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
            focus_id = self.getFocusId()
            if focus_id in self._rows:
                self._maybe_load_more(focus_id)

    def onClick(self, controlID):
        if controlID == 5030:
            self.close()


def _format_count(paged):
    """Show the real total immediately (plan a3f9c2e1), not just what's loaded.

    Plex returns the total alongside the very first page (no extra request),
    so `paged.total` is normally already known right after `load_initial()`.
    """
    count = paged.total if paged.total is not None else len(paged.items)
    return '{} element(s)'.format(count)


def _build_list_item(item):
    li = xbmcgui.ListItem(item['title'], divert_source.item_subtitle(item))
    if item.get('thumb_url'):
        li.setArt({'thumb': item['thumb_url']})
    return li
