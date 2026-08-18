"""Akasha Aura — pure Steam Web API client.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos (see
docs/talos-strategy.md).

Each Akasha OS user configures their own Steam Web API key + SteamID64 in
the addon settings (see decisions.md) — nothing is bundled or committed.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

OWNED_GAMES_URL = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
BOX_ART_URL = 'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'


class SteamAPIError(Exception):
    """Raised when a Steam Web API call fails or returns an unexpected shape."""


class SteamClient:
    """Minimal JSON client for the Steam Web API (owned games library)."""

    def __init__(self, api_key, steam_id, timeout=10):
        self.api_key = (api_key or '').strip()
        self.steam_id = (steam_id or '').strip()
        self.timeout = timeout

    def is_configured(self):
        return bool(self.api_key and self.steam_id)

    def _request(self, url, params):
        if not self.is_configured():
            raise SteamAPIError('Steam API key and SteamID64 are required')
        full_url = url + '?' + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(full_url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:500]
            raise SteamAPIError('Steam API {} error: {}'.format(e.code, body)) from e
        except urllib.error.URLError as e:
            raise SteamAPIError('Steam API URL error: {}'.format(e.reason)) from e
        except json.JSONDecodeError as e:
            raise SteamAPIError('Steam API JSON decode error: {}'.format(e)) from e

    def owned_games_sorted_by_recent(self, limit=60):
        """Return owned games, most recently played first.

        Games never played (rtime_last_played == 0) are sorted last.
        """
        data = self._request(OWNED_GAMES_URL, {
            'key': self.api_key,
            'steamid': self.steam_id,
            'format': 'json',
            'include_appinfo': 1,
            'include_played_free_games': 1,
        })
        games = data.get('response', {}).get('games', [])

        result = [
            {
                'appid': g.get('appid'),
                'name': g.get('name') or 'Jeu Steam #{}'.format(g.get('appid')),
                'playtime_forever': g.get('playtime_forever', 0),
                'last_played': g.get('rtime_last_played', 0),
                'box_art_url': BOX_ART_URL.format(appid=g.get('appid')),
            }
            for g in games
            if g.get('appid')
        ]
        result.sort(key=lambda g: g['last_played'], reverse=True)
        return result[:limit]
