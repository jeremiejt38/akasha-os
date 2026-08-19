"""Akasha Aura — pure configuration helpers.

No dependency on xbmc/xbmcgui/xbmcaddon so this module can be unit tested
with plain python3 -m unittest, and safely delegated to Talos (see
docs/talos-strategy.md).
"""

TABS = ('Divertissement', 'Jeux', 'App', 'Parametres')

DIVERT_SUBTABS = ('Recommande', 'Bibliotheques', 'Categories')
DIVERT_SUBTAB_RECOMMANDE = 0
DIVERT_SUBTAB_BIBLIOTHEQUES = 1
DIVERT_SUBTAB_CATEGORIES = 2

JEUX_SUBTABS = ('SteamLink', 'Moonlight', 'Autres')
APP_SUBTABS = ('Mes Apps', 'Store')


def normalize_server_url(url):
    """Strip whitespace and a trailing slash from a Plex server URL."""
    if not url:
        return ''
    return url.strip().rstrip('/')


def is_plex_configured(server_url, token):
    """Return True if both a server URL and a token are set."""
    return bool(normalize_server_url(server_url)) and bool(token and token.strip())


def build_plex_headers(token):
    """Build the headers required by the Plex API for a given token."""
    return {
        'X-Plex-Token': token or '',
        'Accept': 'application/json',
    }


def default_tab_index(value, tab_count=len(TABS)):
    """Clamp a stored 'default tab' setting value to a valid tab index."""
    try:
        index = int(value)
    except (TypeError, ValueError):
        return 0
    if index < 0 or index >= tab_count:
        return 0
    return index


def default_subtab_index(value, subtab_count=len(DIVERT_SUBTABS)):
    """Clamp a stored 'default subtab' setting value to a valid subtab index."""
    try:
        index = int(value)
    except (TypeError, ValueError):
        return 0
    if index < 0 or index >= subtab_count:
        return 0
    return index


def parse_pinned(raw):
    """Parse a comma-separated list of pinned keys into a list."""
    if not raw:
        return []
    return [item for item in (part.strip() for part in raw.split(',')) if item]


def serialize_pinned(pinned_ids):
    """Serialize a list of keys back into a comma-separated setting format."""
    return ','.join(pinned_ids)


def ordered_items(available, pinned_order, default_first=None):
    """Return available items ordered by pinned_order, then alphabetically.

    `available` is a list of dicts with at least 'key' and 'title'. Items whose
    key is in `pinned_order` come first, in that order; remaining items are
    appended sorted by title. If `default_first` is a key present in the
    result, it is moved to the very front.
    """
    pinned_order = list(pinned_order)
    pinned_set = set(pinned_order)
    by_key = {}
    for item in available:
        key = item.get('key')
        if key:
            by_key[key] = item
    ordered = [by_key[k] for k in pinned_order if k in by_key]
    rest = sorted(
        (item for item in available if item.get('key') not in pinned_set),
        key=lambda item: item.get('title', '').lower(),
    )
    result = ordered + rest
    if default_first and any(item.get('key') == default_first for item in result):
        result = [item for item in result if item.get('key') != default_first]
        result.insert(0, by_key.get(default_first))
    return result
