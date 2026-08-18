"""Akasha Aura — pure Sunshine (LizardByte GameStream host) REST API client.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos (see
docs/talos-strategy.md).

Sunshine (https://github.com/LizardByte/Sunshine) exposes a RESTful API for
its configured "Applications" list, which is what Moonlight clients see as
the games/apps library on a paired host. See docs/aura/decisions.md for the
validation done against a live Sunshine instance: the /api/covers/{index}
endpoint used to serve app cover images is not available on all Sunshine
versions, so cover art here only works when an app's "image-path" is
configured as an absolute http(s) URL — otherwise the tile falls back to
text only.
"""

import base64
import json
import ssl
import urllib.error
import urllib.request


class SunshineAPIError(Exception):
    """Raised when a Sunshine API call fails or returns an unexpected shape."""


def _insecure_ssl_context():
    # Sunshine generates a self-signed TLS certificate for its local web UI
    # by default; there is no CA to validate against on a home LAN, so we
    # deliberately skip verification here (same trust model as connecting
    # Moonlight itself to a paired host).
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class SunshineClient:
    """Minimal JSON client for a Sunshine host's /api/apps endpoint."""

    def __init__(self, server_url, username, password, timeout=10):
        self.server_url = (server_url or '').strip().rstrip('/')
        self.username = (username or '').strip()
        self.password = (password or '').strip()
        self.timeout = timeout

    def is_configured(self):
        return bool(self.server_url and self.username and self.password)

    def _auth_header(self):
        raw = '{}:{}'.format(self.username, self.password).encode('utf-8')
        return 'Basic ' + base64.b64encode(raw).decode('ascii')

    def apps(self):
        """Return the list of applications configured on the Sunshine host."""
        if not self.is_configured():
            raise SunshineAPIError('Sunshine server URL, username and password are required')

        url = self.server_url + '/api/apps'
        req = urllib.request.Request(url, headers={'Authorization': self._auth_header()})
        try:
            with urllib.request.urlopen(
                    req, timeout=self.timeout, context=_insecure_ssl_context()) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:500]
            raise SunshineAPIError('Sunshine API {} error: {}'.format(e.code, body)) from e
        except urllib.error.URLError as e:
            raise SunshineAPIError('Sunshine API URL error: {}'.format(e.reason)) from e
        except json.JSONDecodeError as e:
            raise SunshineAPIError('Sunshine API JSON decode error: {}'.format(e)) from e

        apps = data.get('apps', [])
        result = []
        for index, app in enumerate(apps):
            image_path = app.get('image-path') or ''
            result.append({
                'index': index,
                'name': app.get('name') or 'Application #{}'.format(index),
                'cmd': app.get('cmd', ''),
                # Only absolute URLs are usable as a Kodi texture source;
                # relative paths point at files on the Sunshine host's
                # filesystem, which Aura cannot resolve reliably.
                'box_art_url': image_path if image_path.startswith(('http://', 'https://')) else '',
            })
        return result
