"""Akasha Aura — Plex-style live search (AuraSearch.xml).

Left column: a 6-column letter grid (a-z, 1-0), space/backspace/clear
keys and the recent-query list. Right side: type filter pills
(Tout/Films/Series/Episodes) and a 2-column card grid of results,
refreshed on every keystroke exactly like the Android TV search screen.

Caller sets before doModal():
- `client`       — PlexClient (or connector client with `search`)
- `sections`     — list of Divertissement section dicts to search across
- `on_select`    — callback(item) invoked when a result card is picked
"""
import xbmc
import xbmcgui

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

KEYS_PANEL_ID = 8100
RECENT_LIST_ID = 8110
PILLS_LIST_ID = 8120
RESULTS_PANEL_ID = 8130
SPACE_BUTTON_ID = 8115
BACKSPACE_BUTTON_ID = 8116
CLEAR_BUTTON_ID = 8117
QUERY_LABEL_ID = 8200
EMPTY_LABEL_ID = 8201

_KEYS = list('abcdefghijklmnopqrstuvwxyz') + list('1234567890')
_FILTERS = (
    ('Tout', None),
    ('Films', 'movie'),
    ('Séries', 'show'),
    ('Épisodes', 'episode'),
)


class AuraSearchWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.sections = []
        self.on_select = None
        self.query = ''
        self.recent = []
        self._results = []
        self._filter_index = 0

    def onInit(self):
        try:
            self._render_keyboard()
            self._render_pills()
            self._render_recent()
            self._refresh_query()
            self.setFocus(self.getControl(KEYS_PANEL_ID))
        except Exception as e:
            xbmc.log('Akasha Aura Search: init error: {}'.format(e), xbmc.LOGERROR)

    # ----------------------------------------------------------- rendering

    def _render_keyboard(self):
        try:
            panel = self.getControl(KEYS_PANEL_ID)
            panel.reset()
            for key in _KEYS:
                panel.addItem(xbmcgui.ListItem(key))
        except RuntimeError:
            pass

    def _render_pills(self):
        try:
            pills = self.getControl(PILLS_LIST_ID)
            pills.reset()
            for i, (label, _type) in enumerate(_FILTERS):
                li = xbmcgui.ListItem(label)
                li.setProperty('selected', '1' if i == self._filter_index else '0')
                pills.addItem(li)
        except RuntimeError:
            pass

    def _render_recent(self):
        _set(self, 'AuraSearchHasRecent', '1' if self.recent else '')
        try:
            lst = self.getControl(RECENT_LIST_ID)
            lst.reset()
            for query in self.recent[:8]:
                lst.addItem(xbmcgui.ListItem(query))
        except RuntimeError:
            pass

    def _refresh_query(self):
        try:
            self.getControl(QUERY_LABEL_ID).setLabel(self.query or ' ')
        except RuntimeError:
            pass
        if self.query:
            self._run_search()
        else:
            self._results = []
            self._render_results()

    def _render_results(self):
        _set(self, 'AuraSearchEmpty',
             '1' if self.query and not self._results else '')
        try:
            self.getControl(EMPTY_LABEL_ID).setLabel(
                'Aucun résultat pour « {} »'.format(self.query))
        except RuntimeError:
            pass
        try:
            panel = self.getControl(RESULTS_PANEL_ID)
            panel.reset()
            for item in self._results:
                li = xbmcgui.ListItem(item.get('title') or '', _result_sub(item))
                thumb = item.get('poster_url') or item.get('landscape_url') \
                    or item.get('thumb_url') or 'DefaultVideo.png'
                li.setArt({'poster': thumb})
                li.setProperty('server', item.get('_source') or 'Akasha')
                panel.addItem(li)
        except RuntimeError:
            pass

    # ------------------------------------------------------------- search

    def _run_search(self):
        results = []
        wanted = _FILTERS[self._filter_index][1]
        for section in self.sections:
            try:
                items, _total = self.client.search_with_total(
                    section['key'], self.query, limit=12)
            except Exception as e:
                xbmc.log('Akasha Aura Search: {} failed: {}'.format(
                    section.get('title'), e), xbmc.LOGWARNING)
                continue
            for item in items:
                item['_source'] = section.get('title') or 'Akasha'
            results.extend(items)
        if wanted:
            results = [r for r in results if r.get('type') == wanted]
        # Plex sorts roughly by relevance; keep title-prefix hits first.
        q = self.query.lower()
        results.sort(key=lambda r: 0 if (r.get('title') or '').lower()
                     .startswith(q) else 1)
        self._results = results[:24]
        self._render_results()

    # -------------------------------------------------------------- input

    def onClick(self, controlID):
        if controlID == KEYS_PANEL_ID:
            try:
                pos = self.getControl(KEYS_PANEL_ID).getSelectedPosition()
            except RuntimeError:
                return
            if 0 <= pos < len(_KEYS):
                self.query += _KEYS[pos]
                self._refresh_query()
        elif controlID == SPACE_BUTTON_ID:
            self.query += ' '
            self._refresh_query()
        elif controlID == BACKSPACE_BUTTON_ID:
            self.query = self.query[:-1]
            self._refresh_query()
        elif controlID == CLEAR_BUTTON_ID:
            self.query = ''
            self._refresh_query()
        elif controlID == RECENT_LIST_ID:
            try:
                pos = self.getControl(RECENT_LIST_ID).getSelectedPosition()
            except RuntimeError:
                return
            if 0 <= pos < len(self.recent):
                self.query = self.recent[pos]
                self._refresh_query()
        elif controlID == PILLS_LIST_ID:
            try:
                pos = self.getControl(PILLS_LIST_ID).getSelectedPosition()
            except RuntimeError:
                return
            self._filter_index = pos
            self._render_pills()
            if self.query:
                self._run_search()
        elif controlID == RESULTS_PANEL_ID:
            self._pick_result()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            if self.query and self.query not in self.recent:
                self.recent.insert(0, self.query)
            self.close()
            return
        super().onAction(action)

    def _pick_result(self):
        try:
            pos = self.getControl(RESULTS_PANEL_ID).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._results)):
            return
        if self.query and self.query not in self.recent:
            self.recent.insert(0, self.query)
        if self.on_select:
            self.on_select(self._results[pos])


def _set(window, prop, value):
    window.setProperty(prop, value or '')


def _result_sub(item):
    """Plex-style subtitle: '2018 • Show', 'S5 E1 • Episode'."""
    kind = {'movie': 'Film', 'show': 'Show', 'season': 'Saison',
            'episode': 'Épisode'}.get(item.get('type'), 'Vidéo')
    if item.get('type') == 'episode' and item.get('season') is not None:
        return 'S{} E{} • {}'.format(item.get('season'), item.get('index'), kind)
    if item.get('year'):
        return '{} • {}'.format(item['year'], kind)
    return kind
