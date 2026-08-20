"""Akasha Quick Start -- entry point.

Always shows the wizard from the Bienvenue step when invoked: the
decision of *whether* to invoke it (first boot only vs. a manual
relaunch from Akasha Settings) belongs to the caller
(service.akasha.aura's launcher checks quickstart_state.is_completed(),
the Akasha Settings menu entry always launches it unconditionally), not
to this script.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon('script.akasha.quickstart')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(os.path.join(ADDON_PATH, 'resources', 'lib'))

from quickstart_window import QuickStartWindow  # noqa: E402


def main():
    try:
        window = QuickStartWindow('QuickStart.xml', ADDON_PATH, 'Default', '1080i')
        window.doModal()
        del window
    except Exception as e:
        xbmc.log('Akasha Quick Start: fatal error: {}'.format(e), xbmc.LOGERROR)


if __name__ == '__main__':
    main()
