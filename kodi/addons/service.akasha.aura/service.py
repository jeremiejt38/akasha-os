"""Akasha Aura Launcher — opens Akasha Aura instead of the native Home screen.

Runs once at Kodi startup (xbmc.service, start="startup"). Waits for the
boot intro (service.akasha.splash) to finish so Aura opens right after it,
then launches script.akasha.aura full screen. The native Kodi Home window
is left untouched underneath: pressing Back from Aura still reveals it as a
safety net (see docs/aura/decisions.md).

On a first boot (or any boot before the Quick Start wizard has been
completed, see plan 3aba4284 / script.akasha.quickstart), launches the
wizard instead -- it chains into Aura itself once finished
(quickstart_window.QuickStartWindow._finish()).
"""
import os
import time

import xbmc

INTRO_FLAG_FILE = '/tmp/.akasha-intro-played'
MAX_WAIT_SECONDS = 30
# Mirrors script.akasha.quickstart/resources/lib/quickstart_state.py's
# MARKER_PATH -- duplicated rather than cross-imported from another
# addon's resources/lib for a single path constant, to keep this launcher
# self-contained.
QUICKSTART_MARKER_PATH = '/storage/.config/akasha-os/quickstart-completed'

monitor = xbmc.Monitor()


def _wait_for_intro():
    waited = 0
    while waited < MAX_WAIT_SECONDS and not monitor.abortRequested():
        if os.path.exists(INTRO_FLAG_FILE):
            return
        if monitor.waitForAbort(0.5):
            return
        waited += 0.5


def main():
    _wait_for_intro()
    if monitor.abortRequested():
        return
    if not os.path.exists(QUICKSTART_MARKER_PATH):
        xbmc.log('Akasha Aura Launcher: first run, opening Quick Start', xbmc.LOGINFO)
        xbmc.executebuiltin('RunScript(script.akasha.quickstart)')
        return
    xbmc.log('Akasha Aura Launcher: opening Akasha Aura', xbmc.LOGINFO)
    xbmc.executebuiltin('RunScript(script.akasha.aura)')


if __name__ == '__main__':
    main()
