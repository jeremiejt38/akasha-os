"""Akasha Aura — App tab: installed addons inventory and pinning.

Pure module (no xbmc* import) so it stays unit-testable with plain
`python3 -m unittest`, per docs/talos-strategy.md. JSON-RPC calls and addon
settings persistence are injected by the caller (see aura_app.py), which
does depend on xbmc*.
"""

import json

# Only list addon types that behave like "apps" launchable from Aura:
# Python scripts and plugin sources (programs, streaming apps, games
# launchers, etc). Skins, services, repositories, resources and other
# infrastructure addons are excluded on purpose.
INCLUDED_TYPES = ('xbmc.python.script', 'xbmc.python.pluginsource')

# Never show Akasha's own addons, or system/infrastructure scripts that
# aren't user-facing "apps", in the App inventory.
EXCLUDED_ADDON_IDS = (
    'script.akasha.aura',
    'script.akasha.ambient',
    'script.akasha.guide',
    'script.akasha.launcher',
    'script.akasha.settings',
    'script.skinvariables',
    'script.texturemaker',
    'service.akasha.aura',
    'service.akasha.ambient',
    'service.akasha.overlay',
    'service.akasha.splash',
)

# service.* and virtual.* addons are LibreELEC/Kodi system integrations
# (Argon ONE control, RPi/system tools, etc), never user-launchable apps.
EXCLUDED_ADDON_ID_PREFIXES = ('service.', 'virtual.')


def build_get_addons_request():
    """Build the JSON-RPC request dict for Addons.GetAddons."""
    return {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Addons.GetAddons',
        'params': {
            'installed': True,
            'enabled': True,
            # 'addonid' and 'type' are always returned and are not valid
            # entries for 'properties' (Kodi rejects the request otherwise).
            'properties': ['name', 'version', 'summary', 'icon'],
        },
    }


def parse_get_addons_response(raw_response):
    """Parse the raw JSON-RPC response string into a list of addon dicts."""
    try:
        data = json.loads(raw_response)
    except (TypeError, ValueError):
        return []

    addons = data.get('result', {}).get('addons', [])
    result = []
    for addon in addons:
        addonid = addon.get('addonid') or ''
        if addon.get('type') not in INCLUDED_TYPES:
            continue
        if addonid in EXCLUDED_ADDON_IDS:
            continue
        if addonid.startswith(EXCLUDED_ADDON_ID_PREFIXES):
            continue
        result.append({
            'addonid': addon.get('addonid'),
            'name': addon.get('name') or addon.get('addonid'),
            'version': addon.get('version', ''),
            'summary': addon.get('summary', ''),
            'icon': addon.get('icon', ''),
            'type': addon.get('type'),
        })
    return result


def parse_pinned(raw):
    """Parse the comma-separated 'app.pinned' setting into a list of addon ids."""
    if not raw:
        return []
    return [item for item in (part.strip() for part in raw.split(',')) if item]


def serialize_pinned(pinned_ids):
    """Serialize a list of addon ids back into the comma-separated setting format."""
    return ','.join(pinned_ids)


def toggle_pinned(pinned_ids, addon_id):
    """Return a new pinned list with addon_id toggled in/out."""
    pinned_ids = list(pinned_ids)
    if addon_id in pinned_ids:
        pinned_ids.remove(addon_id)
    else:
        pinned_ids.append(addon_id)
    return pinned_ids


def sort_addons(addons, pinned_ids):
    """Sort addons: pinned first (in pinned order), then the rest alphabetically."""
    pinned_ids = list(pinned_ids)
    by_id = {a['addonid']: a for a in addons}

    pinned = [by_id[aid] for aid in pinned_ids if aid in by_id]
    rest = sorted(
        (a for a in addons if a['addonid'] not in pinned_ids),
        key=lambda a: a['name'].lower(),
    )
    return pinned + rest
