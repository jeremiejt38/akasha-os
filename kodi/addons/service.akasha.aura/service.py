"""Akasha Aura Launcher — opens Akasha Aura instead of the native Home screen.

Runs once at Kodi startup (xbmc.service, start="startup"). Waits for the
boot intro (service.akasha.splash) to finish so Aura opens right after it,
then launches script.akasha.aura full screen. The native Kodi Home window
is left untouched underneath: pressing Back from Aura still reveals it as a
safety net (see docs/aura/decisions.md).
"""
import os
import time

import xbmc

INTRO_FLAG_FILE = '/tmp/.akasha-intro-played'
MAX_WAIT_SECONDS = 30

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
    xbmc.log('Akasha Aura Launcher: opening Akasha Aura', xbmc.LOGINFO)
    xbmc.executebuiltin('RunScript(script.akasha.aura)')


if __name__ == '__main__':
    main()
