"""Akasha Aura — helpers for loading game shortcuts.

No dependency on xbmc* so this module can be unit tested with plain
`python3 -m unittest`, and safely delegated to Talos.
"""

import os
import xml.etree.ElementTree as ET


def _data_xml_path(addon_path):
    return os.path.join(addon_path, 'skin-patches', 'shortcuts', 'games.DATA.xml')


def _parse_shortcut(elem):
    """Convert a <shortcut> element to a dict."""
    return {
        'label': (elem.findtext('label') or '').strip(),
        'label2': (elem.findtext('label2') or '').strip(),
        'icon': (elem.findtext('icon') or '').strip(),
        'thumb': (elem.findtext('thumb') or '').strip(),
        'action': (elem.findtext('action') or '').strip(),
    }


def load_shortcuts(addon_path):
    """Load game shortcuts from the skin-patches games.DATA.xml file."""
    path = _data_xml_path(addon_path)
    if not os.path.exists(path):
        return []

    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []

    root = tree.getroot()
    return [_parse_shortcut(child) for child in root.findall('shortcut')]
