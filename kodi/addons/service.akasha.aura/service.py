"""Akasha Aura Launcher — opens Akasha Aura instead of the native Home screen.

Runs once at Kodi startup (xbmc.service, start="startup"). The boot intro
itself is played pre-Kodi by the systemd splash-video.service (its last
frame is held until Kodi takes over), so this service only waits for the
native Home window to be active with no modal dialog, then launches
script.akasha.aura full screen. Meanwhile the skin's boot veil
(skin-patches/patch_home_boot_veil.py) keeps the AH2 loading screen on
top of the native Home window -- lifted once Aura sets
Window.Property(Akasha.AuraReady) in onInit, or force-lifted here after
AURA_READY_WAIT_SECONDS so the native Home stays reachable as a safety
net (see docs/aura/decisions.md).

On a first boot (or any boot before the Quick Start wizard has been
completed, see plan 3aba4284 / script.akasha.quickstart), launches the
wizard instead -- it chains into Aura itself once finished
(quickstart_window.QuickStartWindow._finish()).
"""
import os
import time

import xbmc
import xbmcgui

# Bounded wait for the native Home window before launching Aura: first-run
# dialogs or a leftover startup notification can still own the screen when
# this service fires. A one-shot check at that exact moment skipped Aura
# permanently and stranded the user on the native Kodi Home.
# NOTE: there used to be a _wait_for_intro() polling /tmp/.akasha-intro-played,
# but nothing writes that flag anymore (the intro moved to the pre-Kodi
# systemd splash-video.service and service.akasha.splash's play_intro is
# dead code) -- it silently wasted the full 30 s timeout at every boot.
HOME_WINDOW_WAIT_SECONDS = 30
# Mirrors script.akasha.quickstart/resources/lib/quickstart_state.py's
# MARKER_PATH -- duplicated rather than cross-imported from another
# addon's resources/lib for a single path constant, to keep this launcher
# self-contained.
QUICKSTART_MARKER_PATH = '/storage/.config/akasha-os/quickstart-completed'

monitor = xbmc.Monitor()


def _wait_for_home_window():
    """Wait until Kodi's native Home window is active with no modal dialog
    on top. Returns False on abort or timeout -- the caller still launches
    Aura in that case, so Home always ends up in Aura."""
    waited = 0
    while waited < HOME_WINDOW_WAIT_SECONDS and not monitor.abortRequested():
        if (xbmcgui.getCurrentWindowId() == 10000
                and xbmcgui.getCurrentWindowDialogId() == 9999):
            return True
        if monitor.waitForAbort(0.5):
            return False
        waited += 0.5
    return False


def main():
    if monitor.abortRequested():
        return
    if not os.path.exists(QUICKSTART_MARKER_PATH):
        xbmc.log('Akasha Aura Launcher: first run, opening Quick Start', xbmc.LOGINFO)
        xbmc.executebuiltin('RunScript(script.akasha.quickstart)')
        return
    if not _wait_for_home_window():
        if monitor.abortRequested():
            return
        xbmc.log('Akasha Aura Launcher: Home window not active after {}s, '
                 'launching Aura anyway'.format(HOME_WINDOW_WAIT_SECONDS),
                 xbmc.LOGWARNING)
    xbmc.log('Akasha Aura Launcher: opening Akasha Aura', xbmc.LOGINFO)
    xbmc.executebuiltin('RunScript(script.akasha.aura)')


if __name__ == '__main__':
    main()
