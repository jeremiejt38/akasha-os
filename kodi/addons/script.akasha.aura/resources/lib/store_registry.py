"""Akasha Aura -- local registry of apps installed via the Akasha OS Store.

Pure module (no xbmc* import) so it stays unit-testable, per
docs/talos-strategy.md. This is the piece plan f4e069bb's Phase 4 relies on
to know which addons "Mes Applications" should show: an addon only appears
there if it (a) is recorded here (installed via the Store) AND (b) still
has a manifest entry in the live index.json (see store_client.py) -- an
addon installed by any other means never shows up, by design.
"""
import json
import os

REGISTRY_PATH = '/storage/.akasha/installed_store_apps.json'


def _default_registry():
    return {'entries': {}}


def load_registry(path=REGISTRY_PATH):
    """Return {app_id: {'version': str, 'installed_at': iso str}}.

    Missing or malformed registry files are treated as empty rather than
    raising -- a corrupted registry should never crash the App tab, just
    make it look like nothing was installed via the Store yet.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}
    entries = data.get('entries', {})
    if not isinstance(entries, dict):
        return {}
    return entries


def _save_registry(entries, path=REGISTRY_PATH):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'entries': entries}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def record_install(app_id, version, installed_at, addon_id=None, path=REGISTRY_PATH):
    """Add/update a registry entry after a successful install.

    `addon_id` is the real Kodi addon id (e.g. "plugin.video.francetv"),
    distinct from `app_id` (the store's own reverse-domain id, e.g.
    "tv.francetv") -- only set for kodi-repo/zip-url installs, which are
    the only types that actually correspond to a real Kodi addon. Kept
    here (not just derivable from the store index) so callers that only
    have the registry on hand, like aura_app.py's addon inventory, can
    cross-reference "is this installed Kodi addon one the Store manages"
    without a network fetch.
    """
    entries = load_registry(path)
    entries[app_id] = {
        'version': version,
        'installed_at': installed_at,
        'addon_id': addon_id,
    }
    _save_registry(entries, path)
    return entries


def record_uninstall(app_id, path=REGISTRY_PATH):
    """Remove a registry entry after a successful uninstall. No-op if
    the app wasn't registered."""
    entries = load_registry(path)
    entries.pop(app_id, None)
    _save_registry(entries, path)
    return entries


def addon_id_to_store_id(registry_entries):
    """Reverse map {kodi_addon_id: store_app_id} for entries that have one
    (kodi-repo/zip-url installs only) -- lets a caller that only knows a
    Kodi addonid (e.g. from Addons.GetAddons) tell whether it's Store-
    managed, without needing the store index itself."""
    return {
        entry['addon_id']: app_id
        for app_id, entry in registry_entries.items()
        if entry.get('addon_id')
    }


def visible_app_ids(registry_entries, index_entries_by_id):
    """Plan f4e069bb Phase 4's strict filter: an app is shown in "Mes
    Applications" only if it is both registered here (installed via the
    Store) AND still present in the live store index (a valid, current
    manifest). Returns the set of ids that pass both checks; ids that are
    registered but have since disappeared from the index are reported
    separately so the caller can log/flag them instead of silently
    dropping them (plan section 5: "log/alerte discrete plutot que
    crash")."""
    registered_ids = set(registry_entries)
    index_ids = set(index_entries_by_id)
    visible = registered_ids & index_ids
    orphaned = registered_ids - index_ids
    return visible, orphaned
