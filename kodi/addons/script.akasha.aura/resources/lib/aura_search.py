"""Akasha Aura — Plex-style live search (AuraSearch.xml).

Left column: a 6-column letter grid (a-z, 1-0), space/backspace/clear
keys and the recent-query list. Right side: type filter pills
(Tout/Films/Series/Episodes) and a 2-column card grid of results,
refreshed on every keystroke exactly like the Android TV search screen.

Caller sets before doModal():
- `client`       — PlexClient (or connector client with `search`)
- `sections`     — list of Divertissement section dicts to search across
- `on_select`    — callback(item) invoked when a result card is picked
- `on_person`    — callback(person dict) for people results
- `on_genre`     — callback(genre dict) for genre results
"""
import datetime
import threading

import xbmc
import xbmcgui
import i18n

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117

KEYS_PANEL_ID = 8100
RECENT_LIST_ID = 8110
PILLS_LIST_ID = 8120
RESULTS_PANEL_ID = 8130
SUGGEST_PANEL_ID = 8131
SPACE_BUTTON_ID = 8115
BACKSPACE_BUTTON_ID = 8116
CLEAR_BUTTON_ID = 8117
QUERY_LABEL_ID = 8200
EMPTY_LABEL_ID = 8201
RAIL_LIST_ID = 8140

_KEYS = list('abcdefghijklmnopqrstuvwxyz') + list('1234567890')
# Plex 2026.19.1's filter rail, in order: All / Movies / TV / Music /
# Live TV / People / Services. Live TV and Services rarely match on a
# local library -- Plex still shows the pills and an empty state.
_FILTERS = (
    (i18n.tr(33052), None),
    (i18n.tr(33051), 'movie'),
    (i18n.tr(33150), 'show'),
    (i18n.tr(33609), 'music'),
    (i18n.tr(33615), 'livetv'),
    (i18n.tr(33152), 'person'),
    (i18n.tr(33614), 'services'),
)

_MUSIC_TYPES = ('artist', 'album', 'track')
_LIVETV_TYPES = ('livetv', 'channel')
_SERVICE_TYPES = ('service', 'cloud', 'online')


class AuraSearchWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.sections = []
        self.on_select = None
        self.on_person = None
        self.on_genre = None
        self.addon = None
        self.query = ''
        self.recent = []
        self._search_gen = 0
        self._results = []
        self._filter_index = 0
        self._recent_loaded = False
        self._genres = None
        self._suggested = None
        self._server_name = None
        self._yield_stop = threading.Event()

    def onInit(self):
        # Same yield-to-playback rule as the main window's
        # _watch_external_playback watchdog: a modal dialog would
        # otherwise keep rendering over the fullscreen video when
        # playback starts from the detail window stacked on top.
        threading.Thread(target=self._watch_playback, daemon=True).start()
        try:
            self._load_recent()
            self._render_rail()
            self._render_keyboard()
            self._render_pills()
            self._render_recent()
            self._refresh_query()
            self.setFocus(self.getControl(KEYS_PANEL_ID))
        except Exception as e:
            xbmc.log('Akasha Aura Search: init error: {}'.format(e), xbmc.LOGERROR)

    def close(self):
        self._yield_stop.set()
        super().close()

    def _watch_playback(self):
        while not self._yield_stop.is_set():
            try:
                if xbmc.Player().isPlayingVideo():
                    self.close()
                    return
            except Exception:
                return
            self._yield_stop.wait(1.0)

    # ----------------------------------------------------------- rendering

    def _render_rail(self):
        """The collapsed 4-icon rail Plex keeps on the search page.
        Icons mirror the main window's sidebar shortcuts; avatar and
        search are informational here, Home/More leave the dialog."""
        try:
            rail = self.getControl(RAIL_LIST_ID)
            rail.reset()
            avatar = xbmcgui.Window(10000).getProperty('AuraAvatar')
            icons = ['avatar-plex.png', 'icon-search.png',
                     'icon-home.png', 'icon-more.png']
            if avatar:
                icons[0] = avatar
            kinds = ('avatar', 'search', 'home', 'menu')
            for i, icon in enumerate(icons):
                li = xbmcgui.ListItem('')
                li.setArt({'icon': icon})
                li.setProperty('iconkind', kinds[i])
                if i == 0 and avatar:
                    li.setProperty('avatar', '1')
                rail.addItem(li)
        except RuntimeError:
            pass

    def _render_keyboard(self):
        try:
            panel = self.getControl(KEYS_PANEL_ID)
            panel.reset()
            for key in _KEYS:
                panel.addItem(xbmcgui.ListItem(key))
        except RuntimeError:
            pass

    def _render_pills(self):
        # Plex's filter pills hug their text: measure each label and
        # chain the static buttons (overlay labels 815x/816x draw the
        # white / amber-selected / dark-on-focus states).
        x = 686
        for i, (label, _type) in enumerate(_FILTERS):
            w = int((i18n.text_width(label, 19) or len(label) * 11)
                    * 0.96) + 56
            try:
                btn = self.getControl(PILLS_LIST_ID + i)
                btn.setPosition(x, 48)
                btn.setWidth(w)
                for base in (8150, 8160, 8170):
                    lbl = self.getControl(base + i)
                    lbl.setPosition(x, 48)
                    lbl.setWidth(w)
                    lbl.setLabel(label)
            except RuntimeError:
                pass
            _set(self, 'AuraSearchPillSel{}'.format(i),
                 '1' if i == self._filter_index else '')
            x += w + 16

    def _render_recent(self):
        # With a query, Plex swaps the left column's search history for
        # plain-text suggestions -- the top hits (people/genres/titles
        # already merged by _run_search) as tappable rows, no icon.
        if self.query:
            rows = self._results[:7]
            _set(self, 'AuraSearchHasRecent', '1' if rows else '')
            try:
                lst = self.getControl(RECENT_LIST_ID)
                lst.reset()
                for item in rows:
                    li = xbmcgui.ListItem(
                        item.get('title') or item.get('name') or '')
                    li.setProperty('suggest', '1')
                    lst.addItem(li)
            except RuntimeError:
                pass
            return
        _set(self, 'AuraSearchHasRecent', '1' if self.recent else '')
        try:
            lst = self.getControl(RECENT_LIST_ID)
            lst.reset()
            for query in self.recent[:8]:
                lst.addItem(xbmcgui.ListItem(query))
            if self.recent:
                clear = xbmcgui.ListItem(i18n.tr(33580))
                clear.setProperty('clear', '1')
                lst.addItem(clear)
        except RuntimeError:
            pass

    def _refresh_query(self):
        try:
            # Plex shows the word "Search" as the field placeholder.
            self.getControl(QUERY_LABEL_ID).setLabel(
                self.query or i18n.tr(33001))
        except RuntimeError:
            pass
        # Serial searches blocked the whole dialog per keystroke on a
        # slow server path (~5s per section); the fetch now runs on a
        # worker and the generation counter drops stale results.
        self._search_gen = getattr(self, '_search_gen', 0) + 1
        if self.query:
            # Plex flips the page instantly: pills replace "Popular
            # Searches" and the left column swaps history for text
            # suggestions -- neither waits on the network fetch.
            _set(self, 'AuraSearchHasQuery', '1')
            _set(self, 'AuraSearchEmpty', '')
            self._results = []
            self._render_recent()
            self._launch_search(self._search_gen)
        else:
            _set(self, 'AuraSearchHasQuery', '')
            # Plex fills the empty results zone with suggested content.
            self._results = self._suggestions()
            self._render_results()

    def _launch_search(self, gen):
        def worker():
            try:
                results = self._collect_results()
            except Exception as e:
                xbmc.log('Akasha Aura Search: collect failed: {}'.format(
                    e), xbmc.LOGERROR)
                return
            if gen != self._search_gen or self._yield_stop.is_set():
                return
            self._results = results[:24]
            self._render_results()
        threading.Thread(target=worker, daemon=True).start()

    def _collect_results(self):
        """Section fetches run in parallel (bounded by the slowest one)
        then get filtered/sorted like Plex's All view."""
        wanted = _FILTERS[self._filter_index][1]
        if wanted == 'person':
            return self._search_people()[:24]
        # Server-side `title=` is a raw substring filter: stray
        # whitespace would exclude exact-title hits, so the API sees
        # the stripped query like Plex's own client sends.
        term = self.query.strip()
        results = []
        lock = threading.Lock()
        # 'Tout' also merges people/genre cards; both are per-section
        # directory walks that must overlap the title searches, not
        # queue behind them.
        side = {}
        if wanted is None:
            for name, fn in (('people', self._search_people),
                             ('genres', self._search_genres)):
                side[name] = threading.Thread(
                    target=lambda f=fn, n=name: side.__setitem__(
                        n + '_r', f()),
                    daemon=True)
                side[name].start()

        def hit(section):
            try:
                items, _total = self.client.search_with_total(
                    section['key'], term, limit=12)
            except Exception as e:
                xbmc.log('Akasha Aura Search: {} failed: {}'.format(
                    section.get('title'), e), xbmc.LOGWARNING)
                return
            with lock:
                for item in items:
                    item['_source'] = section.get('title') or 'Akasha'
                results.extend(items)

        threads = [threading.Thread(target=hit, args=(section,),
                                    daemon=True)
                   for section in self.sections]
        for t in threads:
            t.start()
        # Cap the wait at the slowest section; a hung request must not
        # keep the results frozen when the rest already landed.
        for t in threads:
            t.join(15.0)
        if wanted == 'music':
            results = [r for r in results
                       if r.get('type') in _MUSIC_TYPES]
        elif wanted == 'livetv':
            results = [r for r in results
                       if r.get('type') in _LIVETV_TYPES]
        elif wanted == 'services':
            results = [r for r in results
                       if r.get('type') in _SERVICE_TYPES]
        elif wanted:
            results = [r for r in results if r.get('type') == wanted]
        # Plex sorts roughly by relevance; keep title-prefix hits first.
        q = term.lower()
        results.sort(key=lambda r: 0 if (r.get('title') or '').lower()
                     .startswith(q) else 1)
        # 'Tout' merges matching people and genres first, like Plex's
        # People/genre result cards.
        if wanted is None:
            side['people'].join(15.0)
            side['genres'].join(15.0)
            results = (side.get('people_r', [])[:8]
                       + side.get('genres_r', [])[:4] + results)
        return results[:24]

    def _render_results(self):
        _set(self, 'AuraSearchHasQuery', '1' if self.query else '')
        _set(self, 'AuraSearchEmpty',
             '1' if self.query and not self._results else '')
        try:
            self.getControl(EMPTY_LABEL_ID).setLabel(
                i18n.tr(33072).format(self.query))
        except RuntimeError:
            pass
        try:
            # Plex swaps the results zone layout with the query state:
            # poster grid for Popular Searches, media cards once typed.
            panel = self.getControl(
                RESULTS_PANEL_ID if self.query else SUGGEST_PANEL_ID)
            panel.reset()
            for item in self._results:
                if item.get('_genre'):
                    import divert_source
                    li = xbmcgui.ListItem(
                        divert_source.display_genre(item.get('name') or ''),
                        item.get('section_title') or i18n.tr(33581))
                    li.setArt({'poster': 'DefaultGenre.png'})
                    li.setProperty('genre', '1')
                elif item.get('_person'):
                    li = xbmcgui.ListItem(item.get('name') or '',
                                          item.get('role') or i18n.tr(33127))
                    li.setArt({'poster': item.get('thumb_url')
                                       or 'actor-fallback.png'})
                    li.setProperty('person', '1')
                else:
                    li = xbmcgui.ListItem(
                        i18n.ellipsize(item.get('title') or '', 22),
                        i18n.ellipsize(_result_sub(item) if self.query
                                       else _suggest_sub(item), 19))
                    thumb = item.get('poster_url') or item.get('landscape_url') \
                        or item.get('thumb_url') or 'DefaultVideo.png'
                    li.setArt({'poster': thumb})
                    # Plex's amber line names the server that owns the
                    # result, not the library section.
                    li.setProperty('server', self._server_label())
                    # Episode cards carry a fourth line: the show name
                    # between title and 'S5 E1 • Episode'.
                    if item.get('type') == 'episode' \
                            and item.get('show_title'):
                        li.setProperty('parent', item['show_title'])
                panel.addItem(li)
        except RuntimeError:
            pass
        # The left column mirrors the query state too (suggestions once
        # typed, history while empty) -- refresh it with the results.
        self._render_recent()

    # ------------------------------------------------------------- search

    def _search_genres(self):
        """Genre-name matches, client-side over the per-section genre
        directories (/hubs/search reports genre counts but no items)."""
        if self._genres is None:
            self._genres = []
            if self.client and getattr(self.client, 'section_genres', None):
                import divert_source
                lock = threading.Lock()

                def pull(section):
                    try:
                        raw = self.client.section_genres(section['key'])
                        names = (divert_source.parse_genres(raw)
                                 if isinstance(raw, dict) else raw)
                    except Exception as e:
                        xbmc.log('Akasha Aura Search: genres failed for {}: {}'
                                 .format(section.get('title'), e),
                                 xbmc.LOGWARNING)
                        return
                    with lock:
                        for name in names or []:
                            self._genres.append({
                                '_genre': True, 'name': name,
                                'section_key': section['key'],
                                'section_title': section.get('title') or ''})

                ts = [threading.Thread(target=pull, args=(s,), daemon=True)
                      for s in self.sections]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(15.0)
        q = self.query.strip().lower()
        return [g for g in self._genres if q in (g['name'] or '').lower()]

    def _suggestions(self):
        """Suggested content for the empty-query zone (B8): the first
        discover hubs' items, Plex's trending-style fill.

        Discover returns placeholder hubs with no inline Metadata --
        the posters live behind each hub's `key` continuation, so pull
        one page per hub when `items` is empty (seen on-screen: the
        "Recherches populaires" heading rendered with a blank grid)."""
        if self._suggested is None:
            self._suggested = []
            fetch = getattr(self.client, 'discover_hubs', None)
            if fetch:
                try:
                    for hub in fetch(hub_count=4, per_hub=8):
                        items = list(hub.get('items') or [])
                        key = hub.get('key') or ''
                        if not items and key and \
                                hasattr(self.client, 'hub_items_with_total'):
                            try:
                                items, _ = self.client.hub_items_with_total(
                                    key, limit=8)
                            except Exception:
                                items = []
                        self._suggested.extend(items)
                        if len(self._suggested) >= 12:
                            break
                except Exception as e:
                    xbmc.log('Akasha Aura Search: suggestions failed: {}'
                             .format(e), xbmc.LOGWARNING)
        return self._suggested[:12]

    def _server_label(self):
        """The Plex server's friendlyName for the amber line on result
        cards ('Akasha' on the reference screen). Fetched once; the
        connector client does not expose it so it falls back."""
        if self._server_name is None:
            self._server_name = 'Akasha'
            fetch = getattr(self.client, 'server_friendly_name', None)
            if fetch:
                try:
                    self._server_name = fetch() or 'Akasha'
                except Exception:
                    pass
        return self._server_name

    def _search_people(self):
        """People matching the query (client-side over the per-section
        actor directories -- the hub search reports counts but no items)."""
        if not self.client or not hasattr(self.client, 'search_people'):
            return []
        try:
            return self.client.search_people(self.query.strip())
        except Exception as e:
            xbmc.log('Akasha Aura Search: people failed: {}'.format(e),
                     xbmc.LOGWARNING)
            return []

    def _load_recent(self):
        """Restore past queries persisted in the addon settings so the
        history survives an Aura restart, like Plex's search screen."""
        if self._recent_loaded:
            return
        self._recent_loaded = True
        if self.addon is None:
            return
        import json
        try:
            self.recent = json.loads(
                self.addon.getSetting('search.recent') or '[]')
            if not isinstance(self.recent, list):
                self.recent = []
            # Normalise: stray whitespace makes 'x' and 'x ' look like
            # distinct entries while the stripped query matches the same
            # titles.
            cleaned = []
            for entry in self.recent:
                entry = str(entry).strip()
                if entry and entry not in cleaned:
                    cleaned.append(entry)
            self.recent = cleaned
        except Exception:
            self.recent = []

    def _save_recent(self):
        if self.addon is None:
            return
        import json
        try:
            self.addon.setSetting('search.recent',
                                  json.dumps(self.recent[:8]))
        except Exception:
            pass

    def _push_recent(self, query):
        query = (query or '').strip()
        if query and query not in self.recent:
            self.recent.insert(0, query)
            del self.recent[8:]
            self._save_recent()

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
            if self.query:
                # Suggestion row: opens the hit straight away, like the
                # result card it mirrors.
                if 0 <= pos < len(self._results[:7]):
                    self._open_result(self._results[pos])
            elif pos == len(self.recent[:8]) and self.recent:
                self.recent = []
                self._save_recent()
                self._render_recent()
            elif 0 <= pos < len(self.recent):
                self.query = self.recent[pos]
                self._refresh_query()
        elif PILLS_LIST_ID <= controlID < PILLS_LIST_ID + len(_FILTERS):
            self._filter_index = controlID - PILLS_LIST_ID
            self._render_pills()
            if self.query:
                self._search_gen += 1
                self._launch_search(self._search_gen)
        elif controlID in (RESULTS_PANEL_ID, SUGGEST_PANEL_ID):
            self._pick_result()
        elif controlID == RAIL_LIST_ID:
            # Plex rail over search: the active (search) entry and the
            # avatar do nothing; Home/More leave to the main window.
            try:
                pos = self.getControl(RAIL_LIST_ID).getSelectedPosition()
            except RuntimeError:
                return
            if pos in (2, 3):
                self._push_recent(self.query)
                self.close()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self._push_recent(self.query)
            self.close()
            return
        aid = action.getId()
        try:
            focused = self.getFocusId()
        except RuntimeError:
            focused = -1
        # The right zone swaps panels with the query state (poster grid
        # vs media cards) and Kodi happily focuses a hidden list, so the
        # keyboard's Right and the grids' Left are re-aimed here.
        if aid == 2 and focused in (
                KEYS_PANEL_ID, RECENT_LIST_ID, SPACE_BUTTON_ID,
                BACKSPACE_BUTTON_ID, CLEAR_BUTTON_ID) \
                and not self.query:
            # MOVE_RIGHT off the keyboard with an empty query -- only
            # when the key grid's Right would leave it (last column);
            # mid-row Rights still move between letters.
            if focused == KEYS_PANEL_ID:
                try:
                    pos = self.getControl(KEYS_PANEL_ID) \
                        .getSelectedPosition()
                except RuntimeError:
                    pos = -1
                if pos >= 0 and pos % 6 != 5:
                    super().onAction(action)
                    return
            try:
                self.setFocusId(SUGGEST_PANEL_ID)
            except RuntimeError:
                pass
            return
        if aid == 1 and focused == SUGGEST_PANEL_ID:
            # MOVE_LEFT off the suggestions grid back to the keyboard.
            try:
                self.setFocusId(KEYS_PANEL_ID)
            except RuntimeError:
                pass
            return
        if aid == ACTION_CONTEXT_MENU:
            # Plex long-press: media result cards open the option
            # sheet; keyboard/pills/recent entries keep the
            # long-press == click parity.
            try:
                if focused in (RESULTS_PANEL_ID, SUGGEST_PANEL_ID):
                    self._result_sheet()
                    return
            except RuntimeError:
                pass
            try:
                self.onClick(focused)
            except Exception:
                pass
            return
        super().onAction(action)

    def _results_panel_id(self):
        return RESULTS_PANEL_ID if self.query else SUGGEST_PANEL_ID

    def _result_sheet(self):
        try:
            pos = self.getControl(
                self._results_panel_id()).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._results)):
            return
        item = self._results[pos]
        if item.get('_person') or item.get('_genre'):
            self._pick_result()
            return
        import context_sheet
        context_sheet.open_sheet(
            self, self.client, item, self._results_panel_id(),
            self._pick_result,
            on_removed=lambda p: self._results.pop(p)
            if p < len(self._results) else None)

    def _pick_result(self):
        try:
            pos = self.getControl(
                self._results_panel_id()).getSelectedPosition()
        except RuntimeError:
            return
        if not (0 <= pos < len(self._results)):
            return
        item = self._results[pos]
        self._open_result(item)

    def _open_result(self, item):
        if item.get('_person'):
            if self.on_person:
                self.on_person(item)
            return
        if item.get('_genre'):
            self._push_recent(self.query)
            if self.on_genre:
                self.on_genre(item)
            return
        self._push_recent(self.query)
        if self.on_select:
            self.on_select(item)


def _set(window, prop, value):
    window.setProperty(prop, value or '')


def _suggest_sub(item):
    """Popular-Searches card subtitle like the Plex reference: 'N
    saison(s)' for a show, the full release date when it is still in
    the future, otherwise the bare year -- never 'year • type'."""
    if item.get('type') == 'show' and item.get('child_count'):
        return i18n.tr_count(item['child_count'], 33128)
    avail = str(item.get('originally_available_at') or '')[:10]
    if avail > datetime.date.today().isoformat():
        return i18n.fmt_air_date(avail)
    return str(item.get('year') or '')


def _result_sub(item):
    """Plex-style subtitle: '2018 • Show', 'S5 E1 • Episode'."""
    kind = {'movie': i18n.tr(33133), 'show': i18n.tr(33101),
            'season': i18n.tr(33135), 'episode': i18n.tr(33136)}.get(
            item.get('type'), i18n.tr(33132))
    if item.get('type') == 'episode' and item.get('season') is not None:
        return 'S{} E{} • {}'.format(item.get('season'), item.get('index'), kind)
    if item.get('year'):
        return '{} • {}'.format(item['year'], kind)
    return kind
