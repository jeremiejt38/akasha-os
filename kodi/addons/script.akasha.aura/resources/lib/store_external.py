"""Akasha Aura — Akasha Store: pure helpers for `external-app` web apps.

These functions intentionally do **not** import `xbmc*` so they stay
unit-testable with plain `python3 -m unittest`, per docs/talos-strategy.md.
High-level orchestration (dialogs, JSON-RPC, actual process launch) lives in
`aura_store.py` and `aura_app.py`.

Design goals:
- Never execute or trust arbitrary data from a manifest: only http/https URLs
  are accepted as `source_url` or `deep_link`.
- Keep the local registry as the single source of truth for installed external
  apps; synthetic addon dicts are built from it at display time.
- Re-use the existing cloud-gaming Docker launcher (`launch.sh`) for Chromium,
  so the watchdog/return-to-Kodi path is identical.
"""

import re
from urllib.parse import urlparse

EXTERNAL_ADDON_ID_PREFIX = 'external:'
DEFAULT_LAUNCH_SCRIPT = '/storage/.kodi/scripts/cloud-gaming/launch.sh'
STORE_RAW_BASE = 'https://raw.githubusercontent.com/jeremiejt38/akasha-os-store/main/apps'


def is_valid_http_url(url):
    """Return True only for a plain, non-empty http/https URL with a host.

    This is the gatekeeper for every `external-app` source_url/deep_link: it
    rejects javascript:, file:, data:, relative paths, empty strings and other
    non-web schemes before any of them are stored, displayed or launched.
    """
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    return bool(parsed.netloc)


def validate_install(source_url, deep_link=None):
    """Validate the install block of an `external-app` manifest entry.

    Returns `(True, '')` when the source URL is a valid http/https URL and the
    optional deep_link, if present, is also valid. Otherwise returns
    `(False, <human-readable error>)`.
    """
    if not is_valid_http_url(source_url):
        return False, 'source_url is not a valid http/https URL'
    if deep_link is not None and deep_link != '':
        if not is_valid_http_url(deep_link):
            return False, 'deep_link is not a valid http/https URL'
    return True, ''


def _first_non_empty(*values):
    for value in values:
        if value:
            return value
    return ''


def external_addon_id(store_app_id):
    """Stable synthetic Kodi-style addon id for an external web app."""
    return '{}{}'.format(EXTERNAL_ADDON_ID_PREFIX, store_app_id)


def resolve_icon_url(store_app_id, icon):
    if is_valid_http_url(icon):
        return icon.strip()
    if not isinstance(icon, str) or not icon.strip():
        return ''
    return '{}/{}/{}'.format(
        STORE_RAW_BASE, store_app_id, icon.strip().lstrip('/'))


def _sanitize_unit_name(app_id):
    """Make a store app id safe for use in a systemd unit name."""
    return re.sub(r'[^A-Za-z0-9_.\\-]', '_', str(app_id))


def build_synthetic_addon(store_app_id, index_entry=None, registry_entry=None):
    """Build a display-ready addon dict for a registered `external-app`.

    The `index_entry` (live catalogue entry) is preferred for name/icon because
    it is the freshest, but the `registry_entry` is used as a fallback so the
    app still appears even when the catalogue is offline.
    """
    index = index_entry or {}
    registry = registry_entry or {}

    # `install` may live either in the live manifest or in the registry.
    install = index.get('install') or registry.get('install') or {}
    if not isinstance(install, dict):
        install = {}

    name = _first_non_empty(
        index.get('name'), registry.get('name'), store_app_id)
    version = _first_non_empty(
        index.get('version'), registry.get('version'), '')
    summary = _first_non_empty(
        index.get('description'), index.get('summary'),
        registry.get('description'), registry.get('summary'), '')
    icon = resolve_icon_url(store_app_id, _first_non_empty(
        index.get('icon'), index.get('thumbnail'),
        registry.get('icon'), registry.get('thumbnail'), ''))

    source_url = install.get('source_url', '') if isinstance(install, dict) else ''
    deep_link = _first_non_empty(
        index.get('deep_link'), install.get('deep_link'), registry.get('deep_link'))

    return {
        'addonid': external_addon_id(store_app_id),
        'name': name,
        'version': version,
        'summary': summary,
        'icon': icon,
        'type': 'external-app',
        'is_external': True,
        'store_id': store_app_id,
        'source_url': source_url,
        'deep_link': deep_link,
    }


def build_synthetic_addons(registry, index_by_id=None):
    """Return display-ready addon dicts for every `external-app` in `registry`.

    Only registry entries whose persisted `install.type` is `external-app` are
    turned into synthetic addons. The live `index_by_id` is used for display
    metadata when available, but the apps are kept even if the catalogue is
    unreachable (the user explicitly chose to keep all registered apps).
    """
    index_by_id = index_by_id or {}
    result = []
    for app_id, reg in registry.items():
        if not isinstance(reg, dict):
            continue
        install = reg.get('install') if isinstance(reg, dict) else None
        if not isinstance(install, dict) or install.get('type') != 'external-app':
            continue
        entry = index_by_id.get(app_id)
        synthetic = build_synthetic_addon(app_id, index_entry=entry, registry_entry=reg)
        result.append(synthetic)
    return sorted(result, key=lambda a: a['name'].lower())


def launch_command_args(source_url, name, deep_link=None, app_id=None,
                        launch_script_path=DEFAULT_LAUNCH_SCRIPT):
    """Build the Popen argument list to launch an external app in Chromium.

    Reuses the cloud-gaming Docker launcher (`launch.sh`) so the watchdog and
    return-to-Kodi path is identical to the existing cloud-gaming flow. The
    effective URL is `deep_link` when provided, otherwise `source_url`.
    """
    url = deep_link if deep_link else source_url
    unit = 'external-app-{}'.format(_sanitize_unit_name(app_id) if app_id else 'generic')
    return [
        'systemd-run', '--unit=' + unit, '--collect',
        '/bin/bash', launch_script_path, url, name,
    ]
