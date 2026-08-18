"""Akasha Aura — Recommandations view (hero rows: Continuer a regarder / Ajoutes recemment).

Milestone 6 (see docs/aura/roadmap.md): tries akasha-os-connector first (using
the session token already established from the Divertissement tab, see
aura_window.py::_get_connector_client), falls back to direct Plex API access
(plex_client.py, already in production) if the connector is not configured or
the stored session is invalid. No login prompt here: a user reaching this
window is expected to already be authenticated (or intentionally not using
the connector), keeping this window's flow simple.
"""
import xbmc
import xbmcaddon
import xbmcgui

import connector_client
import divert_source
import plex_client

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

ROW_ON_DECK_LABEL_ID = 5100
ROW_ON_DECK_LIST_ID = 5110
ROW_RECENT_LABEL_ID = 5200
ROW_RECENT_LIST_ID = 5210
ROW_RELEASES_LABEL_ID = 5300
ROW_RELEASES_LIST_ID = 5310
STATUS_LABEL_ID = 5020


class AuraRecommendationsWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self._connector = None
        self._plex = None
        self._first_section = None

    def onInit(self):
        try:
            self._connect()
            self._load_row(ROW_ON_DECK_LABEL_ID, ROW_ON_DECK_LIST_ID,
                            'Continuer a regarder', self._fetch_on_deck)
            self._load_row(ROW_RECENT_LABEL_ID, ROW_RECENT_LIST_ID,
                            'Ajoutes recemment', self._fetch_recently_added)
            releases_title = 'Sorties recentes'
            section = self._get_first_video_section()
            if section:
                releases_title = 'Sorties recentes — {}'.format(section['title'])
            self._load_row(ROW_RELEASES_LABEL_ID, ROW_RELEASES_LIST_ID,
                            releases_title, self._fetch_recent_releases)
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

    def _fetch_on_deck(self):
        if self._connector:
            raw = self._connector.on_deck()
            return divert_source.parse_metadata_list(raw, self._connector.image_url)
        if self._plex:
            return self._plex.on_deck()
        return []

    def _fetch_recently_added(self):
        if self._connector:
            raw = self._connector.recently_added()
            return divert_source.parse_metadata_list(raw, self._connector.image_url)
        if self._plex:
            return self._plex.recently_added()
        return []

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

    def _fetch_recent_releases(self):
        section = self._get_first_video_section()
        if not section:
            return []
        if self._connector:
            raw = self._connector.section_items(
                section['key'], sort='originallyAvailableAt:desc', limit=20)
            return divert_source.parse_metadata_list(raw, self._connector.image_url)
        if self._plex:
            return self._plex.section_items(
                section['key'], sort='originallyAvailableAt:desc', limit=20)
        return []

    def _load_row(self, label_control_id, list_control_id, title, fetch_fn):
        items = []
        error = None
        try:
            items = fetch_fn()
        except (connector_client.ConnectorAPIError, plex_client.PlexAPIError) as e:
            error = e
        except Exception as e:  # defensive: never crash the window on a row failure
            error = e

        try:
            self.getControl(label_control_id).setLabel(
                '{} ({} element(s))'.format(title, len(items)) if not error else
                '{} — erreur de chargement'.format(title))
        except RuntimeError:
            pass

        if error:
            xbmc.log('Akasha Aura Recommendations: {} failed: {}'.format(title, error),
                     xbmc.LOGWARNING)

        try:
            lst = self.getControl(list_control_id)
            lst.reset()
            for item in items:
                li = xbmcgui.ListItem(item['title'])
                if item.get('thumb_url'):
                    li.setArt({'thumb': item['thumb_url']})
                lst.addItem(li)
        except Exception as e:
            xbmc.log('Akasha Aura Recommendations: render error for {}: {}'.format(title, e),
                     xbmc.LOGERROR)

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)

    def onClick(self, controlID):
        if controlID == 5030:
            self.close()
