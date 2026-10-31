"""Akasha Aura -- settings catalog (plan b81d3f6a).

Declarative description of the unified settings menu: root categories,
their rows, and which source backs each row. Every row shows the *real*
current value through its source (settings_engine.py) -- nothing here is
a static label.

Item schema (dict):
    id       unique id (stack/focus key)
    type     header | info | bool | enum | int | string | action | dynamic
    label    i18n msgid (i18n.py STRINGS table)
    help     i18n msgid for the right-pane contextual help (optional)
    source   typed source tuple:
               ('kodi',   <setting_id>)
               ('addon',  <addon_id>, <key>)
               ('system', (<backend>, <op>))
               ('custom', <registry name>)
               ('action', <builtin>)         -- runs executebuiltin
               ('window', <window name>)     -- ActivateWindow (closes Aura)
               ('script', <script id>)       -- RunScript (closes Aura)
               ('addonui', <addon id>)       -- RunAddon (closes Aura)
    options  for 'enum' with static choices: [(value, i18n-or-literal)]
    range    for 'int' pickers: (min, max, step, unit i18n msgid or '')
    secret   mask the string value / hidden input
    visible_if  callable(backend, cache) -> bool (optional)

Category schema:
    id, title (i18n msgid), summary (callable or None), items[]
"""


def _kodi_categories():
    return [
        {
            'id': 'network',
            'title': 33250,
            'summary': None,
            'items': [
                {'id': 'net.status', 'type': 'info', 'label': 33401,
                 'source': ('system', ('connman', 'net_status'))},
                {'id': 'net.ip', 'type': 'info', 'label': 33402,
                 'source': ('system', ('connman', 'ip_address'))},
                {'id': 'net.wifi', 'type': 'bool', 'label': 33403,
                 'help': 33404,
                 'source': ('system', ('connman', 'wifi_enabled'))},
                {'id': 'net.le', 'type': 'action', 'label': 33405,
                 'help': 33406,
                 'source': ('addonui', 'service.libreelec.settings')},
            ],
        },
        {
            'id': 'display_sound',
            'title': 33255,
            'summary': None,
            'items': [
                {'id': 'vid.resolution', 'type': 'enum', 'label': 33410,
                 'help': 33411,
                 'source': ('kodi', 'videoscreen.resolution')},
                {'id': 'vid.refresh', 'type': 'enum', 'label': 33412,
                 'help': 33413,
                 'source': ('kodi', 'videoplayer.adjustrefreshrate')},
                {'id': 'aud.device', 'type': 'enum', 'label': 33414,
                 'help': 33415,
                 'source': ('kodi', 'audiooutput.audiodevice')},
                {'id': 'aud.channels', 'type': 'enum', 'label': 33416,
                 'help': 33417,
                 'source': ('kodi', 'audiooutput.channels')},
                {'id': 'aud.passthrough', 'type': 'bool', 'label': 33418,
                 'help': 33419,
                 'source': ('kodi', 'audiooutput.passthrough')},
                {'id': 'aud.ac3', 'type': 'bool', 'label': 33420,
                 'source': ('kodi', 'audiooutput.ac3passthrough'),
                 'visible_if': 'dep:aud.passthrough'},
                {'id': 'aud.dts', 'type': 'bool', 'label': 33421,
                 'source': ('kodi', 'audiooutput.dtspassthrough'),
                 'visible_if': 'dep:aud.passthrough'},
                {'id': 'vid.calibration', 'type': 'action', 'label': 33422,
                 'help': 33423,
                 'source': ('window', 'screencalibration')},
            ],
        },
        {
            'id': 'accounts',
            'title': 33253,
            'summary': None,
            'items': [
                {'id': 'acc.plex', 'type': 'action', 'label': 33430,
                 'help': 33431,
                 'source': ('addonui', 'script.plexmod'),
                 'summary_fn': 'acc.plex'},
                {'id': 'acc.jellyfin', 'type': 'action', 'label': 33432,
                 'source': ('addonui', 'plugin.video.jellyfin')},
                {'id': 'acc.youtube', 'type': 'action', 'label': 33433,
                 'source': ('addonui', 'plugin.video.youtube')},
                {'id': 'acc.plex_url', 'type': 'string', 'label': 33434,
                 'source': ('addon', 'script.akasha.aura', 'plex.server_url')},
                {'id': 'acc.plex_token', 'type': 'string', 'label': 33435,
                 'secret': True,
                 'source': ('addon', 'script.akasha.aura', 'plex.token')},
                {'id': 'acc.steam_key', 'type': 'string', 'label': 33436,
                 'secret': True,
                 'source': ('addon', 'script.akasha.aura', 'steam.api_key')},
                {'id': 'acc.steam_id', 'type': 'string', 'label': 33437,
                 'source': ('addon', 'script.akasha.aura', 'steam.steam_id')},
                {'id': 'acc.sun_url', 'type': 'string', 'label': 33438,
                 'source': ('addon', 'script.akasha.aura',
                            'sunshine.server_url')},
                {'id': 'acc.sun_user', 'type': 'string', 'label': 33439,
                 'source': ('addon', 'script.akasha.aura',
                            'sunshine.username')},
                {'id': 'acc.sun_pass', 'type': 'string', 'label': 33440,
                 'secret': True,
                 'source': ('addon', 'script.akasha.aura',
                            'sunshine.password')},
            ],
        },
        {
            'id': 'controllers',
            'title': 33257,
            'summary': None,
            'items': [
                {'id': 'bt.devices', 'type': 'dynamic', 'label': 33450,
                 'help': 33451,
                 'source': ('system', ('bluetooth', 'paired_devices'))},
                {'id': 'bt.pair', 'type': 'action', 'label': 33452,
                 'help': 33453,
                 'source': ('addonui', 'service.libreelec.settings')},
                {'id': 'remote.cfg', 'type': 'action', 'label': 33454,
                 'source': ('action',
                            'Addon.OpenSettings(service.akasha.remote)')},
            ],
        },
        {
            'id': 'playback',
            'title': 33260,
            'summary': None,
            'items': [
                {'id': 'play.audio_lang', 'type': 'enum', 'label': 33460,
                 'help': 33461,
                 'source': ('kodi', 'locale.audiolanguage')},
                {'id': 'play.sub_lang', 'type': 'enum', 'label': 33462,
                 'help': 33463,
                 'source': ('kodi', 'locale.subtitlelanguage')},
                {'id': 'play.kodi', 'type': 'action', 'label': 33464,
                 'source': ('window', 'playersettings')},
            ],
        },
        {
            'id': 'appearance',
            'title': 33263,
            'summary': None,
            'items': [
                {'id': 'app.language', 'type': 'enum', 'label': 33470,
                 'help': 33471,
                 'source': ('kodi', 'locale.language')},
                {'id': 'app.country', 'type': 'enum', 'label': 33472,
                 'source': ('kodi', 'locale.country')},
                {'id': 'app.datefmt', 'type': 'enum', 'label': 33473,
                 'source': ('kodi', 'locale.shortdateformat')},
                {'id': 'app.timefmt', 'type': 'enum', 'label': 33474,
                 'source': ('kodi', 'locale.timeformat')},
                {'id': 'app.tzcountry', 'type': 'enum', 'label': 33475,
                 'source': ('kodi', 'locale.timezonecountry')},
                {'id': 'app.tz', 'type': 'enum', 'label': 33476,
                 'source': ('kodi', 'locale.timezone')},
                {'id': 'app.ss_time', 'type': 'int', 'label': 33477,
                 'help': 33478,
                 'range': (0, 60, 5, 'min'),
                 'source': ('kodi', 'screensaver.time')},
                {'id': 'app.ambient', 'type': 'bool', 'label': 33479,
                 'help': 33480,
                 'source': ('addon', 'script.akasha.settings',
                            'ambient.enabled')},
                {'id': 'app.overlay', 'type': 'bool', 'label': 33481,
                 'source': ('addon', 'script.akasha.settings',
                            'overlay.enabled')},
            ],
        },
        {
            'id': 'power',
            'title': 33269,
            'summary': None,
            'items': [
                {'id': 'pwr.display_off', 'type': 'int', 'label': 33490,
                 'help': 33491,
                 'range': (0, 60, 5, 'min'),
                 'source': ('kodi', 'powermanagement.displaysoff')},
                {'id': 'pwr.shutdown', 'type': 'int', 'label': 33492,
                 'help': 33493,
                 'range': (0, 120, 15, 'min'),
                 'source': ('kodi', 'powermanagement.shutdowntime')},
                {'id': 'pwr.state', 'type': 'enum', 'label': 33494,
                 'source': ('kodi', 'powermanagement.shutdownstate')},
            ],
        },
        {
            'id': 'system',
            'title': 33272,
            'summary': None,
            'items': [
                {'id': 'sys.hostname', 'type': 'info', 'label': 33500,
                 'source': ('system', ('sysinfo', 'hostname'))},
                {'id': 'sys.akasha_ver', 'type': 'info', 'label': 33501,
                 'source': ('custom', 'akasha.version')},
                {'id': 'sys.le_ver', 'type': 'info', 'label': 33502,
                 'source': ('custom', 'le.version')},
                {'id': 'sys.cpu_temp', 'type': 'info', 'label': 33503,
                 'source': ('system', ('sysinfo', 'cpu_temp'))},
                {'id': 'sys.mem', 'type': 'info', 'label': 33504,
                 'source': ('system', ('sysinfo', 'free_mem'))},
                {'id': 'sys.updates', 'type': 'enum', 'label': 33505,
                 'help': 33506,
                 'source': ('kodi', 'general.addonupdates')},
                {'id': 'sys.unknown', 'type': 'bool', 'label': 33507,
                 'help': 33508,
                 'source': ('kodi', 'addons.unknownsources')},
                {'id': 'sys.akasha', 'type': 'action', 'label': 33509,
                 'source': ('script', 'script.akasha.settings')},
                {'id': 'sys.backup', 'type': 'action', 'label': 33510,
                 'help': 33511,
                 'source': ('addonui', 'service.libreelec.settings')},
            ],
        },
        {
            'id': 'advanced',
            'title': 33207,
            'summary': None,
            'items': [
                {'id': 'adv.kodi', 'type': 'action', 'label': 33278,
                 'source': ('window', 'settings')},
                {'id': 'adv.le', 'type': 'action', 'label': 33279,
                 'source': ('addonui', 'service.libreelec.settings')},
                {'id': 'adv.profiles', 'type': 'action', 'label': 33276,
                 'source': ('window', 'profilesettings')},
                {'id': 'adv.files', 'type': 'action', 'label': 33520,
                 'source': ('window', 'filemanager')},
                {'id': 'adv.skin', 'type': 'action', 'label': 33265,
                 'source': ('window', 'skinsettings')},
            ],
        },
    ]


# Plex's settings sheet leads with Account, then Player Experience,
# Video & Audio, Experience... and closes on Advanced (official
# 49-settings). Aura's catalog covers the OS on top of Plex's scope,
# so the order is echoed rather than the entries renamed.
_PLEX_ORDER = ('accounts', 'playback', 'display_sound', 'appearance',
               'network', 'controllers', 'power', 'system', 'advanced')


def build_categories():
    order = {cid: i for i, cid in enumerate(_PLEX_ORDER)}
    return sorted(_kodi_categories(),
                  key=lambda c: order.get(c['id'], 99))


def kodi_setting_ids(categories=None):
    """All ('kodi', id) sources -- used by the catalog validation test."""
    out = []
    for cat in (categories or build_categories()):
        for item in cat['items']:
            src = item.get('source') or ()
            if src and src[0] == 'kodi':
                out.append(src[1])
    return out
