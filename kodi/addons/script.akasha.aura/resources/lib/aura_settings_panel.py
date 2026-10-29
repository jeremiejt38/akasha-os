"""Akasha Aura -- Unified Settings panel (plan b81d3f6a).

Android TV-style *real* settings menu: a stack of views inside a single
WindowXML dialog -- root categories, a category's setting rows, then a
radio picker (or a Kodi keyboard) for the value being changed. Replaces
the previous implementation which only listed shortcuts to native
screens: every row here reads and writes the actual underlying value
through settings_engine's typed sources (Kodi JSON-RPC, addon settings,
connman/bluetooth/system). The few things that genuinely cannot be
reimplemented (Wi-Fi pairing UI, addon account flows) keep a clearly
marked shortcut to their native screen.

Layout: left = the current view's list (categories / settings / radio
options), right = contextual help for the focused row (Android TV's
right pane).
"""
import threading

import xbmc
import xbmcgui

import i18n
import settings_catalog
import settings_engine

LIST_ID = 100
HEADER_LABEL_ID = 10
SUBHEADER_LABEL_ID = 11
HELP_LABEL_ID = 20

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_BACKSPACE = 110
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2


def _tr(msgid):
    return i18n.tr(msgid)


class _View(object):
    """One stack level: what the list currently shows."""

    def __init__(self, kind, title, payload=None, pos=0):
        self.kind = kind           # root | category | picker | bt_devices | bt_device
        self.title = title
        self.payload = payload     # category dict | item dict | devices | device
        self.pos = pos             # focus position to restore on pop
        self.rows = []             # rendered row descriptors


class AuraSettingsPanelWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = settings_engine.Backend()
        self.cache = settings_engine.KodiSettingsCache(self.backend)
        self.categories = settings_catalog.build_categories()
        self._stack = []
        self._navigating = False
        # Set by AuraWindow._open_settings_panel() before doModal(): Aura's
        # own window, closed alongside this panel before firing a
        # native-window action (see the comment there for why).
        self.parent_window = None
        # Rail replica snapshot (same mechanism as the profile menu):
        # Plex keeps the expanded sidebar readable behind its settings
        # sheet, but Kodi dims the parent window under a modal dialog.
        self.rail_items = []
        self.rail_props = {}
        # Set when the user picks a row in the rail replica: the parent
        # activates that real sidebar entry after the dialog closes.
        self.rail_selection = -1
        # 'account' opens the panel straight on the Plex-style Account
        # sheet (official-live/51) instead of the OS categories; the
        # caller passes the /api/v2/user dict via account_user.
        self.start_view = None
        self.account_user = {}

    # ------------------------------------------------------------------
    # Lifecycle / navigation
    # ------------------------------------------------------------------

    def _populate_rail_replica(self):
        try:
            rail = self.getControl(9020)
        except RuntimeError:
            return
        try:
            rail.reset()
        except (AttributeError, RuntimeError):
            pass
        for it in self.rail_items:
            li = xbmcgui.ListItem(it.get('label', ''))
            if it.get('icon'):
                li.setArt({'icon': it['icon']})
            for prop in ('is_profile', 'is_header', 'is_library'):
                if it.get(prop):
                    li.setProperty(prop, it[prop])
            rail.addItem(li)
        for key, val in self.rail_props.items():
            try:
                self.setProperty(key, val)
            except RuntimeError:
                pass

    def onInit(self):
        if self.rail_items:
            self._populate_rail_replica()
        if self.start_view == 'account':
            self._push(_View('account', _tr(33627)))
        else:
            self._push(_View('root', _tr(33019)))

    def _push(self, view):
        if self._stack:
            top = self._stack[-1]
            try:
                top.pos = self.getControl(LIST_ID).getSelectedPosition()
            except RuntimeError:
                top.pos = 0
        self._stack.append(view)
        self._render()

    def _pop(self):
        if len(self._stack) <= 1:
            self.close()
            return
        self._stack.pop()
        self._render()

    def _render(self):
        """Rebuild the list for the top view. Positions are restored from
        the view's saved `pos`; ListItems are never reused across views."""
        view = self._stack[-1]
        try:
            self.getControl(HEADER_LABEL_ID).setLabel(view.title)
        except RuntimeError:
            pass
        view.rows = self._build_rows(view)
        items = []
        for row in view.rows:
            li = xbmcgui.ListItem(row['label'])
            li.setLabel2(row.get('value', ''))
            li.setProperty('kind', row.get('kind', 'item'))
            li.setProperty('help', row.get('help', ''))
            if row.get('checked'):
                li.setProperty('checked', 'true')
            if 'switch' in row:
                li.setProperty('switch', 'on' if row['switch'] else 'off')
            items.append(li)
        try:
            control = self.getControl(LIST_ID)
            control.reset()
            if items:
                control.addItems(items)
                self.setFocus(control)
                pos = min(view.pos, len(items) - 1)
                control.selectItem(max(0, pos))
            self._refresh_help()
        except RuntimeError as e:
            xbmc.log('Akasha Aura Settings: render error: {}'.format(e),
                     xbmc.LOGERROR)

    def _build_rows(self, view):
        if view.kind == 'account':
            return self._account_rows()
        if view.kind == 'root':
            return [self._category_row(cat) for cat in self.categories]
        if view.kind == 'category':
            rows = []
            for item in view.payload['items']:
                row = self._item_row(item)
                if row is not None:
                    rows.append(row)
            return rows
        if view.kind == 'picker':
            current = view.payload['current']
            rows = []
            for opt in view.payload['options']:
                rows.append({
                    'kind': 'radio', 'label': opt['label'],
                    'checked': opt['value'] == current,
                    'option': opt,
                })
            return rows
        if view.kind == 'bt_devices':
            devices = view.payload or []
            if not devices:
                return [{'kind': 'info', 'label': _tr(33540), 'value': ''}]
            return [{'kind': 'item', 'label': d['name'], 'value': '',
                     'device': d} for d in devices]
        if view.kind == 'bt_device':
            return [
                {'kind': 'item', 'label': _tr(33536), 'op': 'connect'},
                {'kind': 'item', 'label': _tr(33537), 'op': 'disconnect'},
                {'kind': 'item', 'label': _tr(33538), 'op': 'remove'},
            ]
        return []

    _AUTO_SIGN_IN_ITEM = {
        'id': 'auto_sign_in', 'type': 'bool', 'label': 33632,
        'source': ('addon', 'script.akasha.aura', 'plex.auto_sign_in'),
    }

    def _account_rows(self):
        """Plex's Account sheet (official-live/51): identity rows from
        plex.tv /api/v2/user, then the app-level preferences. Rows whose
        counterpart lives on plex.tv only are stubbed like the account
        menu's cloud entries."""
        u = self.account_user or {}
        rows = [
            {'kind': 'info', 'label': _tr(33628),
             'value': str(u.get('email') or '-')},
            {'kind': 'info', 'label': _tr(33629),
             'value': str(u.get('username') or u.get('title') or '-')},
        ]
        sub = u.get('subscription') or {}
        if (isinstance(sub, dict) and sub.get('active')) \
                or u.get('plexPass') or u.get('hasPlexPass'):
            rows.append({'kind': 'info', 'label': _tr(33630),
                         'value': _tr(33631)})
        rows.append(self._item_row(self._AUTO_SIGN_IN_ITEM))
        rows.append({'kind': 'info', 'label': _tr(33633),
                     'value': xbmc.getLanguage() or '-'})
        rows.append({'kind': 'stub', 'label': _tr(33634)})
        # Aura always reports watch state/ratings back to the Plex
        # server, so Plex's toggle is effectively On here.
        rows.append({'kind': 'info', 'label': _tr(33635),
                     'value': _tr(33530)})
        rows.append({'kind': 'stub', 'label': _tr(33636)})
        rows.append({'kind': 'stub', 'label': _tr(33637)})
        rows.append({'kind': 'stub', 'label': _tr(33638)})
        return [r for r in rows if r]

    def _category_row(self, cat):
        return {'kind': 'category', 'label': _tr(cat['title']),
                'value': self._category_summary(cat), 'category': cat}

    def _category_summary(self, cat):
        """Android TV-style subtitle under a root category: the formatted
        value of its first informative row (Ethernet connecté, 1080p…)."""
        first = cat['items'][0] if cat['items'] else None
        if first is None:
            return ''
        row = self._item_row(first, summary_only=True)
        return row['value'] if row else ''

    # ------------------------------------------------------------------
    # Row construction -- reads REAL current values through the sources.
    # ------------------------------------------------------------------

    def _source_get(self, item):
        src = item.get('source') or ()
        kind = src[0] if src else ''
        if kind == 'kodi':
            if not self.cache.has(src[1]):
                return _MISSING
            return self.cache.get(src[1])
        if kind == 'addon':
            try:
                return self.backend.addon_get(src[1], src[2])
            except Exception:
                return _MISSING
        if kind == 'system':
            source = settings_engine.SystemSource(src[1])
            return source.get(self.backend, self.cache)
        if kind == 'custom':
            source = settings_engine.CustomSource(src[1])
            return source.get(self.backend, self.cache)
        return None

    def _source_options(self, item):
        src = item.get('source') or ()
        if src and src[0] == 'kodi':
            options = [{'value': o['value'], 'label': o['label']}
                       for o in self.cache.options(src[1])]
            if options:
                return options
        if item.get('range'):
            # int delay presets -- radio picker like Android TV rather
            # than the numeric keypad.
            lo, hi, step, unit = item['range']
            out = []
            for v in range(int(lo), int(hi) + 1, int(step)):
                if unit == 'min' and v == 0:
                    out.append({'value': v, 'label': _tr(33543)})
                elif unit == 'min':
                    out.append({'value': v, 'label': _tr(33544).format(v)})
                else:
                    out.append({'value': v, 'label': str(v)})
            return out
        return [{'value': v, 'label': _tr(l) if isinstance(l, int) else l}
                for v, l in (item.get('options') or [])]

    def _source_set(self, item, value):
        src = item.get('source') or ()
        kind = src[0] if src else ''
        ok = False
        if kind == 'kodi':
            ok = self.cache.set(src[1], value)
        elif kind == 'addon':
            try:
                self.backend.addon_set(src[1], src[2], value)
                ok = True
            except Exception:
                ok = False
        elif kind == 'system':
            ok = settings_engine._system_set(
                self.backend, src[1][0], src[1][1], value)
        if not ok:
            self.backend.notify(_tr(33547))
        return ok

    def _dep_item(self, item):
        """visible_if 'dep:<item_id>' -> that sibling item."""
        dep = item.get('visible_if') or ''
        if not dep.startswith('dep:'):
            return None
        dep_id = dep[4:]
        view = self._stack[-1]
        if view.kind != 'category':
            return None
        for it in view.payload['items']:
            if it['id'] == dep_id:
                return it
        return None

    def _item_row(self, item, summary_only=False):
        """Build a row descriptor for a catalog item, or None when the
        row must be hidden (unknown Kodi id, unmet visible_if dep)."""
        if item['type'] in ('action',):
            return {'kind': 'action', 'label': _tr(item['label']),
                    'value': self._action_subtitle(item),
                    'help': _tr(item['help']) if item.get('help') else '',
                    'item': item}
        if item['type'] == 'dynamic':
            return {'kind': 'item', 'label': _tr(item['label']),
                    'value': self._dynamic_summary(item),
                    'help': _tr(item['help']) if item.get('help') else '',
                    'item': item}
        dep = self._dep_item(item)
        if dep is not None:
            dep_val = self._source_get(dep)
            if dep_val in (_MISSING, None, False, 'false', '0', ''):
                return None
        value = self._source_get(item)
        if value is _MISSING:
            return None
        if item['type'] == 'info':
            return {'kind': 'info', 'label': _tr(item['label']),
                    'value': self._format_value(item, value),
                    'item': item}
        if item['type'] == 'bool':
            on = value in (True, 'true', '1', 1)
            return {'kind': 'item', 'label': _tr(item['label']),
                    'value': _tr(33530) if on else _tr(33531),
                    'switch': on, 'item': item,
                    'help': _tr(item['help']) if item.get('help') else ''}
        return {'kind': 'item', 'label': _tr(item['label']),
                'value': self._format_value(item, value),
                'help': _tr(item['help']) if item.get('help') else '',
                'item': item}

    def _format_value(self, item, value):
        src = item.get('source') or ()
        if value is None or value is _MISSING:
            return ''
        if src and src[0] == 'system':
            return self._format_system(src[1], value)
        if item['type'] == 'enum':
            for opt in self._source_options(item):
                if opt['value'] == value:
                    return opt['label']
            return str(value)
        if item['type'] == 'int':
            if item.get('range') and item['range'][3] == 'min':
                if value == 0:
                    return _tr(33543)
                return _tr(33544).format(value)
            return str(value)
        if item.get('secret'):
            return '••••••••' if value else _tr(33533)
        return str(value) if value else _tr(33533)

    def _format_system(self, spec, value):
        backend_name, op = spec
        if op == 'net_status':
            if not value or not value.get('kind'):
                return _tr(33545)
            if value['kind'] == 'wifi':
                return _tr(33532).format(value['name'])
            return _tr(33548)
        if op == 'cpu_temp' and value is not None:
            return _tr(33541).format(value)
        if op == 'free_mem' and value is not None:
            return _tr(33542).format(value)
        return '' if value is None else str(value)

    def _action_subtitle(self, item):
        fn = item.get('summary_fn')
        if fn == 'acc.plex':
            try:
                url = self.backend.addon_get('script.akasha.aura',
                                             'plex.server_url')
                return _tr(33534) if url else _tr(33533)
            except Exception:
                return _tr(33533)
        return ''

    def _dynamic_summary(self, item):
        src = item.get('source') or ()
        if src[0] != 'system':
            return ''
        if src[1] == ('bluetooth', 'paired_devices'):
            devices = settings_engine._system_get(
                self.backend, 'bluetooth', 'paired_devices')
            n = len(devices or [])
            return _tr(33539).format(n) if n else _tr(33540)
        return ''

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_BACKSPACE):
            self._pop()
            return
        super().onAction(action)
        if aid == ACTION_MOVE_RIGHT:
            # Android TV: Right drills into the row like a click (except
            # inline switches, which Center alone toggles).
            try:
                pos = self.getControl(LIST_ID).getSelectedPosition()
                rows = self._stack[-1].rows
                if 0 <= pos < len(rows) and 'switch' not in rows[pos]:
                    self.onClick(LIST_ID)
            except RuntimeError:
                pass
            return
        if aid == ACTION_MOVE_LEFT:
            return
        self._refresh_help()

    def _refresh_help(self):
        try:
            pos = self.getControl(LIST_ID).getSelectedPosition()
            rows = self._stack[-1].rows
            text = rows[pos].get('help', '') if 0 <= pos < len(rows) else ''
            self.getControl(HELP_LABEL_ID).setLabel(text)
        except RuntimeError:
            pass

    def onClick(self, controlID):
        if controlID == 9020:
            # Rail replica row picked: hand the index back to the real
            # sidebar, which activates the entry after close (Plex lets
            # the rail stay interactive under the settings sheet).
            try:
                self.rail_selection = \
                    self.getControl(9020).getSelectedPosition()
            except RuntimeError:
                self.rail_selection = -1
            self.close()
            return
        if controlID != LIST_ID or self._navigating:
            return
        try:
            pos = self.getControl(LIST_ID).getSelectedPosition()
        except RuntimeError:
            return
        view = self._stack[-1]
        if not (0 <= pos < len(view.rows)):
            return
        self._navigating = True
        try:
            self._activate(view, view.rows[pos], pos)
        finally:
            self._navigating = False

    def _activate(self, view, row, pos):
        if view.kind == 'account':
            item = row.get('item')
            if row.get('kind') == 'stub':
                self.backend.notify(_tr(33613))
            elif item is not None and item['type'] == 'bool':
                self._toggle_bool(view, row, pos, item)
            return
        if view.kind == 'root':
            cat = row['category']
            self._push(_View('category', _tr(cat['title']), cat))
            return
        if view.kind == 'picker':
            self._pick_option(view, row)
            return
        if view.kind == 'bt_devices':
            device = row.get('device')
            if device:
                self._push(_View('bt_device', device['name'], device))
            return
        if view.kind == 'bt_device':
            self._bt_action(view, row)
            return
        item = row.get('item')
        if item is None:
            return
        if row.get('kind') == 'action':
            self._run_action(item)
        elif item['type'] == 'bool':
            self._toggle_bool(view, row, pos, item)
        elif item['type'] in ('enum', 'int'):
            if self._source_options(item):
                self._open_picker(item)
            elif item['type'] == 'int' or \
                    isinstance(self._source_get(item), int):
                # Kodi 'int' settings carry no options -- numeric input.
                # A non-numeric enum without options degrades to a
                # read-only row rather than a broken editor.
                self._edit_int(view, item)
        elif item['type'] == 'string':
            self._edit_string(view, item)
        elif item['type'] == 'dynamic':
            self._open_dynamic(item)

    # ------------------------------------------------------------------
    # Value editing
    # ------------------------------------------------------------------

    def _toggle_bool(self, view, row, pos, item):
        current = self._source_get(item)
        on = current in (True, 'true', '1', 1)
        src = item.get('source') or ()
        new_value = ('false' if on else 'true') if src[0] == 'addon' \
            else (not on)
        if self._source_set(item, new_value):
            self._render()

    def _open_picker(self, item):
        options = self._source_options(item)
        current = self._source_get(item)
        self._push(_View('picker', _tr(item['label']), {
            'item': item, 'options': options, 'current': current,
        }, pos=max(0, [i for i, o in enumerate(options)
                       if o['value'] == current] or [0])[0]))

    def _pick_option(self, view, row):
        item = view.payload['item']
        self._source_set(item, row['option']['value'])
        self._pop()

    def _edit_int(self, view, item):
        current = self._source_get(item)
        entered = self.backend.input_numeric(
            _tr(item['label']), '' if current is None else str(current))
        if not entered:
            return
        try:
            if self._source_set(item, int(entered)):
                self._render()
        except (ValueError, TypeError):
            pass

    def _edit_string(self, view, item):
        current = self._source_get(item)
        default = '' if current in (None, _MISSING) else str(current)
        entered = self.backend.input_text(
            _tr(item['label']), default, hidden=bool(item.get('secret')))
        # Dialog().input returns '' both on cancel and on confirmed-empty
        # -- indistinguishable, so an empty setting can't be cleared here.
        if not entered or entered == default:
            return
        if self._source_set(item, entered):
            self._render()

    def _open_dynamic(self, item):
        src = item.get('source') or ()
        if src[1] == ('bluetooth', 'paired_devices'):
            devices = settings_engine._system_get(
                self.backend, 'bluetooth', 'paired_devices')
            self._push(_View('bt_devices', _tr(item['label']), devices))

    def _bt_action(self, view, row):
        device = view.payload
        if settings_engine._system_set(
                self.backend, 'bluetooth', row['op'], device['mac']):
            self._stack.pop()          # leave the device-actions view
            # Rebuild the devices list fresh after the action.
            top = self._stack.pop()
            devices = settings_engine._system_get(
                self.backend, 'bluetooth', 'paired_devices')
            self._push(_View('bt_devices', _tr(33450), devices,
                             pos=top.pos))
        else:
            self.backend.notify(_tr(33547))

    # ------------------------------------------------------------------
    # Native screens -- the closing contract is unchanged from the old
    # panel: addon dialogs stack fine over Aura, but base windows must be
    # brought forward by closing this panel AND Aura first.
    # ------------------------------------------------------------------

    def _run_action(self, item):
        src = item.get('source') or ()
        kind = src[0]
        if kind == 'action':
            builtin = src[1]
        elif kind == 'window':
            builtin = 'ActivateWindow({})'.format(src[1])
        elif kind == 'script':
            builtin = 'RunScript({})'.format(src[1])
        elif kind == 'addonui':
            builtin = 'RunAddon({})'.format(src[1])
        else:
            return
        self.close()
        if self.parent_window is not None:
            try:
                self.parent_window.close()
            except Exception:
                pass
        try:
            self.backend.exec_builtin(builtin)
        except Exception as e:
            xbmc.log('Akasha Aura Settings: action failed: {}'.format(e),
                     xbmc.LOGERROR)


class _Missing(object):
    def __repr__(self):
        return '<missing>'


_MISSING = _Missing()
