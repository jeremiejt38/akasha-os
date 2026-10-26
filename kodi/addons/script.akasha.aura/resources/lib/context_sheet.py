"""Akasha Aura — Plex long-press option sheet, shared across windows.

Plex's Android TV long-press opens a small action sheet whose entries
depend on the element under focus: playable items get Play/Resume/
Restart, everything gets Open, rateable entries get Mark-as-watched +
Rate, then the cloud-limited "Add to list" and a File Info dump for
media-bearing items. Navigation elements (sidebar, genre cards) keep
the plain long-press == click parity and never reach this module.

The sheet works on any window that can supply `getControl()` and a Plex
client -- the home window, the person page, and the search window all
reuse it. Playback marks the *opening* window (playback_started +
_playback_item) so the parent can propagate the lifecycle the same way
the detail page does.
"""

import xbmc
import xbmcgui
import aura_menu
import i18n
import osd_menu


def open_sheet(win, client, item, control_id, open_default,
               on_removed=None):
    """Show the Plex option sheet for `item` selected in `control_id`.

    `open_default` is the plain-click action; `on_removed(pos)` is an
    optional hook letting the caller drop the card from its backing
    store after 'Remove from Continue Watching'."""
    typ = item.get('type')
    rateable = typ in ('movie', 'show', 'season', 'episode') \
        and item.get('rating_key') and client is not None
    offset = item.get('view_offset_ms') or 0
    watched = (item.get('view_count') or 0) > 0

    entries = []
    if typ in ('movie', 'episode') and item.get('part_key'):
        entries.append((i18n.tr(33156) if offset else i18n.tr(33104),
                        lambda: play_item(win, client, item)))
        if offset:
            entries.append((i18n.tr(33107),
                            lambda: play_item(win, client, item,
                                              start_over=True)))
    entries.append((i18n.tr(33155), open_default))
    if offset and hasattr(client, 'remove_from_continue_watching'):
        entries.append((i18n.tr(33161),
                        lambda: remove_continue_watching(
                            win, client, item, control_id, on_removed)))
    if rateable:
        entries.append((i18n.tr(33113) if watched else i18n.tr(33112),
                        lambda: toggle_watched(win, client, item,
                                               control_id)))
        entries.append((i18n.tr(33111), lambda: rate(client, item, win)))
    if item.get('video_label') or item.get('audio_label'):
        entries.append((i18n.tr(33116), lambda: file_info(win, item)))

    idx = aura_menu.contextmenu(win,
                                [label for label, _ in entries])
    if 0 <= idx < len(entries):
        entries[idx][1]()


def hydrate_item(client, item):
    """Grid/row payloads usually carry part_key already; shallow hub
    items get one fetch of full metadata."""
    if item.get('part_key') or not item.get('rating_key'):
        return item
    if not client:
        return item
    try:
        full = client.metadata_item(item['rating_key'])
        if isinstance(full, dict) and full:
            full.setdefault('type', item.get('type'))
            item = full
    except Exception as e:
        xbmc.log('Akasha Aura: item hydration failed: {}'.format(e),
                 xbmc.LOGWARNING)
    return item


def play_item(win, client, item, start_over=False):
    """Direct playback from the option sheet -- same modal lifecycle
    as the detail page: every dialog leaves the screen before the
    video starts, and default.py re-opens Aura once it ends."""
    item = hydrate_item(client, item)
    base = getattr(client, 'server_url', None) if client else None
    token = getattr(client, 'token', None) if client else None
    url = ('{}{}?X-Plex-Token={}'.format(base, item['part_key'], token)
           if base and token and item.get('part_key') else None)
    if not url:
        xbmcgui.Dialog().notification(
            'Akasha Aura', i18n.tr(33075),
            xbmcgui.NOTIFICATION_INFO, 2000)
        return
    import aura_detail
    li = xbmcgui.ListItem(item.get('title') or '')
    aura_detail.AuraDetailWindow._apply_info_tags(li, item)
    if item.get('view_offset_ms') and not start_over:
        aura_detail.apply_resume_point(li, item)
    li.setMimeType('video/mp4')
    win.playback_started = True
    win._playback_item = item
    win.close()
    # Single-item play + serialized season queue: the Up Next card
    # (B1) is the decision point between episodes instead of Kodi's
    # silent playlist auto-advance.
    queue = aura_detail.episode_queue_items(client, item)
    osd_menu.store_playback_context(client, queue or [item])
    xbmc.Player().play(url, li)


def toggle_watched(win, client, item, control_id):
    if not client or not item.get('rating_key'):
        return
    watched = (item.get('view_count') or 0) > 0
    try:
        if watched:
            client.unscrobble(item['rating_key'])
        else:
            client.scrobble(item['rating_key'])
    except Exception as e:
        xbmc.log('Akasha Aura: watched toggle failed: {}'.format(e),
                 xbmc.LOGERROR)
        return
    item['view_count'] = 0 if watched else 1
    try:
        li = win.getControl(control_id).getSelectedItem()
        li.getVideoInfoTag().setPlayCount(item['view_count'])
    except Exception:
        pass
    xbmcgui.Dialog().notification(
        'Akasha Aura',
        i18n.tr(33119) if watched else i18n.tr(33118),
        xbmcgui.NOTIFICATION_INFO, 1500)


def remove_continue_watching(win, client, item, control_id,
                             on_removed=None):
    """Plex 'Remove from Continue Watching': dedicated endpoint, then
    drop the card from the row locally so the hub visually matches."""
    if not client or not item.get('rating_key'):
        return
    try:
        client.remove_from_continue_watching(item['rating_key'])
    except Exception as e:
        xbmc.log('Akasha Aura: removeFromContinueWatching failed: {}'
                 .format(e), xbmc.LOGERROR)
        return
    item['view_offset_ms'] = 0
    try:
        ctrl = win.getControl(control_id)
        pos = ctrl.getSelectedPosition()
        if on_removed is not None:
            on_removed(pos)
        ctrl.removeItem(pos)
    except (RuntimeError, IndexError):
        pass
    xbmcgui.Dialog().notification(
        'Akasha Aura', i18n.tr(33146),
        xbmcgui.NOTIFICATION_INFO, 1500)


def rate(client, item, win):
    if not client or not item.get('rating_key'):
        return
    choices = ['{} / 10'.format(i) for i in range(1, 11)]
    pos = aura_menu.select(win, i18n.tr(33111), choices)
    if pos < 0:
        return
    try:
        client.rate(item['rating_key'], pos + 1)
        xbmcgui.Dialog().notification(
            'Akasha Aura', i18n.tr(33120).format(choices[pos]),
            xbmcgui.NOTIFICATION_INFO, 1500)
    except Exception as e:
        xbmc.log('Akasha Aura: rate failed: {}'.format(e), xbmc.LOGERROR)


def file_info(win, item):
    def _fmt_duration(duration_ms):
        if not duration_ms:
            return ''
        total = int(duration_ms) // 1000 // 60
        return '{} h {:02d}'.format(total // 60, total % 60) \
            if total >= 60 else '{} min'.format(total)

    lines = [item.get('title') or '']
    meta = [x for x in (item.get('year'),
                        _fmt_duration(item.get('duration_ms')))
            if x]
    if meta:
        lines.append(' · '.join(str(m) for m in meta))
    for label, key in ((i18n.tr(33132), 'video_label'),
                       (i18n.tr(33201), 'audio_label'),
                       (i18n.tr(33115), 'subtitle_label')):
        if item.get(key):
            lines.append('{} : {}'.format(label, item[key]))
    aura_menu.message(win, i18n.tr(33116), '[CR]'.join(lines))
