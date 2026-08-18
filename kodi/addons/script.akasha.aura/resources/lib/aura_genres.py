"""Akasha Aura — Categories (genres) browser.

Milestone 6 (see docs/aura/roadmap.md): lists the genres of the first video
section (connector-first, Plex-direct fallback, same pattern as
aura_recommendations.py), opens AuraLibraryWindow pre-filtered to the
selected genre.
"""
import xbmc
import xbmcaddon
import xbmcgui

import aura_library
import connector_client
import divert_source
import plex_client

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

STATUS_LABEL_ID = 6020
GENRE_PANEL_ID = 6010


class AuraGenresWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = xbmcaddon.Addon('script.akasha.aura')
        self._connector = None
        self._plex = None
        self.section = None
        self.genres = []
        # Reused across opens rather than a fresh instance each time -- see
        # the note in aura_window.py's AuraWindow.__init__ about why: each
        # WindowXMLDialog construction permanently consumes one of Kodi's
        # ~100 dynamic script-window IDs for the rest of the Kodi session.
        self._library_window = None

    def onInit(self):
        try:
            self._connect()
            self.section = self._first_video_section()
            if not self.section:
                self.getControl(STATUS_LABEL_ID).setLabel(
                    'Aucune bibliotheque video disponible')
                return
            self.genres = self._fetch_genres()
            self.getControl(STATUS_LABEL_ID).setLabel(
                '{} — {} categorie(s)'.format(self.section['title'], len(self.genres)))
            panel = self.getControl(GENRE_PANEL_ID)
            panel.reset()
            for genre in self.genres:
                panel.addItem(xbmcgui.ListItem(genre))
        except Exception as e:
            xbmc.log('Akasha Aura Genres: init error: {}'.format(e), xbmc.LOGERROR)

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

    def _first_video_section(self):
        sections = []
        if self._connector:
            try:
                sections = divert_source.parse_sections(self._connector.sections())
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Genres: connector sections failed, falling back to '
                         'Plex direct: {}'.format(e), xbmc.LOGWARNING)
                self._connector = None
        if not sections and self._plex:
            sections = self._plex.video_sections()
        return sections[0] if sections else None

    def _fetch_genres(self):
        if self._connector:
            try:
                return divert_source.parse_genres(self._connector.section_genres(self.section['key']))
            except connector_client.ConnectorAPIError as e:
                xbmc.log('Akasha Aura Genres: connector genres failed, falling back to Plex '
                         'direct: {}'.format(e), xbmc.LOGWARNING)
                self._connector = None
        if self._plex:
            return self._plex.section_genres(self.section['key'])
        return []

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        super().onAction(action)

    def onClick(self, controlID):
        if controlID == 6030:
            self.close()
        elif controlID == GENRE_PANEL_ID:
            pos = self.getControl(GENRE_PANEL_ID).getSelectedPosition()
            if 0 <= pos < len(self.genres):
                if self._library_window is None:
                    self._library_window = aura_library.AuraLibraryWindow(
                        'AuraLibrary.xml', self.addon.getAddonInfo('path'), 'Default', '1080i')
                self._library_window.initial_section = self.section
                self._library_window.initial_genre = self.genres[pos]
                self._library_window.doModal()
