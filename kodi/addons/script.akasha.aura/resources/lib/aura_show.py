"""Akasha Aura — TV show browser: Seasons -> Episodes drill-down.

Milestone 7 (see docs/aura/roadmap.md): unlike movies (which have a single
metadata entry directly playable), Plex TV shows are structured as
show -> seasons -> episodes. This WindowXMLDialog lets the user drill down
from a show into its seasons, then into a season's episodes.

The caller (aura_window.py) must set `show_title`, `show_rating_key` and
`client` (a configured plex_client.PlexClient) on the instance before
calling doModal().
"""
import xbmc
import xbmcgui

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

LEVEL_SEASONS = 'seasons'
LEVEL_EPISODES = 'episodes'


class AuraShowWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.show_title = ''
        self.show_rating_key = None
        self.level = LEVEL_SEASONS
        self.seasons = []
        self.episodes = []
        self.current_season = None

    def onInit(self):
        try:
            self._load_seasons()
        except Exception as e:
            xbmc.log('Akasha Aura Show: init error: {}'.format(e), xbmc.LOGERROR)

    def _load_seasons(self):
        self.level = LEVEL_SEASONS
        try:
            self.seasons = self.client.show_seasons(self.show_rating_key)
        except Exception as e:
            xbmc.log('Akasha Aura Show: season load failed: {}'.format(e), xbmc.LOGERROR)
            self.seasons = []
        self._render()

    def _load_episodes(self, season):
        self.level = LEVEL_EPISODES
        self.current_season = season
        try:
            self.episodes = self.client.season_episodes(season['rating_key'])
        except Exception as e:
            xbmc.log('Akasha Aura Show: episode load failed: {}'.format(e), xbmc.LOGERROR)
            self.episodes = []
        self._render()

    def _current_items(self):
        return self.seasons if self.level == LEVEL_SEASONS else self.episodes

    def _render(self):
        try:
            header = self.getControl(7000)
            if self.level == LEVEL_SEASONS:
                header.setLabel(self.show_title)
            else:
                header.setLabel('{} — {}'.format(self.show_title, self.current_season['title']))
        except RuntimeError:
            pass

        items = self._current_items()
        try:
            status = self.getControl(7020)
            noun = 'saison(s)' if self.level == LEVEL_SEASONS else 'episode(s)'
            status.setLabel('{} {}'.format(len(items), noun))
        except RuntimeError:
            pass

        try:
            lst = self.getControl(7010)
            lst.reset()
            for item in items:
                li = xbmcgui.ListItem(item['title'])
                if item.get('thumb_url'):
                    li.setArt({'thumb': item['thumb_url']})
                lst.addItem(li)
            if items:
                self.setFocus(lst)
        except Exception as e:
            xbmc.log('Akasha Aura Show: render error: {}'.format(e), xbmc.LOGERROR)

    def onClick(self, controlID):
        if controlID == 7010:
            try:
                pos = self.getControl(7010).getSelectedPosition()
            except RuntimeError:
                return
            items = self._current_items()
            if not (0 <= pos < len(items)):
                return
            item = items[pos]
            if self.level == LEVEL_SEASONS:
                self._load_episodes(item)
            else:
                # Playback delegation is not decided yet (docs/aura/decisions.md).
                xbmcgui.Dialog().notification(
                    'Akasha Aura', item['title'], xbmcgui.NOTIFICATION_INFO, 2000)
        elif controlID == 7030:
            self._go_back()

    def _go_back(self):
        if self.level == LEVEL_EPISODES:
            self._load_seasons()
        else:
            self.close()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._go_back()
            return
        super().onAction(action)
