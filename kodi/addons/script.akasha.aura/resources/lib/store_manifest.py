"""Akasha Aura — Akasha Store: curated addon manifest.

Pure module (no xbmc* import) so it stays unit-testable, per
docs/talos-strategy.md. Installing addons (xbmc.executebuiltin) and
detecting the currently installed set (JSON-RPC) are handled by the caller
(see aura_store.py).
"""

import json
import os

MANIFEST_FILENAME = 'store_manifest.json'


def _manifest_path(addon_path):
    return os.path.join(addon_path, 'resources', 'data', MANIFEST_FILENAME)


def load_manifest(addon_path):
    """Load the curated addon manifest bundled with the addon.

    Returns a list of {'addonid', 'name', 'summary'} dicts, or an empty list
    if the manifest is missing or malformed.
    """
    path = _manifest_path(addon_path)
    if not os.path.exists(path):
        return []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (ValueError, OSError):
        return []

    entries = data.get('entries', [])
    return [
        {
            'addonid': entry.get('addonid'),
            'name': entry.get('name') or entry.get('addonid'),
            'summary': entry.get('summary', ''),
        }
        for entry in entries
        if entry.get('addonid')
    ]


def with_install_status(entries, installed_ids):
    """Annotate each manifest entry with an 'installed' boolean."""
    installed_ids = set(installed_ids)
    return [
        dict(entry, installed=entry['addonid'] in installed_ids)
        for entry in entries
    ]
