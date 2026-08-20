"""Akasha Quick Start -- entry point.

Whether to invoke this at all (first boot only vs. a manual relaunch
from Akasha Settings) belongs to the caller (service.akasha.aura's
launcher checks quickstart_state.is_completed(), the Akasha Settings
menu entry always launches it unconditionally), not to this script.

What this script *does* decide: whether to resume an interrupted run
where it left off (default -- section 1's "sauvegarde progressive": a
boot-time re-launch after an earlier interruption should not force the
user back through steps already validated) or to restart from
Bienvenue (passed explicitly as the "restart" argument by the manual
relaunch entry -- a deliberate "reconfigure everything" action).
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon('script.akasha.quickstart')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(os.path.join(ADDON_PATH, 'resources', 'lib'))

from quickstart_window import QuickStartWindow  # noqa: E402
import quickstart_state as state  # noqa: E402


def main():
    restart = 'restart' in sys.argv[1:]
    try:
        window = QuickStartWindow('QuickStart.xml', ADDON_PATH, 'Default', '1080i')
        window.initial_step = state.STEP_WELCOME if restart else state.get_last_step()
        window.doModal()
        del window
    except Exception as e:
        xbmc.log('Akasha Quick Start: fatal error: {}'.format(e), xbmc.LOGERROR)


if __name__ == '__main__':
    main()
