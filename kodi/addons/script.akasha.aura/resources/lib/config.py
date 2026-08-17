"""Akasha Aura — pure configuration helpers.

No dependency on xbmc/xbmcgui/xbmcaddon so this module can be unit tested
with plain python3 -m unittest, and safely delegated to Talos (see
docs/talos-strategy.md).
"""

TABS = ('Divertissement', 'Jeux', 'App')


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
