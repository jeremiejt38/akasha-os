"""Akasha Splash — Boot intro video service.

Plays the splash intro video once when Kodi starts, then lets the
Home screen appear normally. The video can be skipped by pressing
any button on the remote/controller.

This is a Kodi service addon (replaces deprecated autoexec.py).
"""
import xbmc
import xbmcaddon
import xbmcgui
import os
import json

INTRO_PATH = "/storage/.kodi/media/splash-intro.mp4"
FLAG_FILE = "/tmp/.akasha-intro-played"
UPDATE_STATUS_FILE = "/storage/.config/akasha-os/update-status.json"

addon = xbmcaddon.Addon()
monitor = xbmc.Monitor()


def show_update_success():
    """If an OTA update just happened, show success + changelog dialogs."""
    if not os.path.exists(UPDATE_STATUS_FILE):
        return

    try:
        with open(UPDATE_STATUS_FILE, 'r') as f:
            status = json.load(f)
    except Exception:
        os.remove(UPDATE_STATUS_FILE)
        return

    old_version = status.get('old_version', 'Inconnue')
    new_version = status.get('new_version', 'Inconnue')
    changelog = status.get('changelog', '')

    # Wait a moment for Kodi to be fully ready
    monitor.waitForAbort(1)

    xbmc.log("Akasha Splash: showing update success dialog for {}".format(new_version), xbmc.LOGINFO)

    dialog = xbmcgui.Dialog()
    dialog.ok(
        'Akasha OS - Mise a jour reussie',
        'Le systeme a ete mis a jour avec succes.\n\n'
        '{} -> {}'.format(old_version, new_version)
    )

    if changelog:
        dialog.textviewer(
            'Akasha OS - Changelog v{}'.format(new_version),
            changelog
        )

    # Delete the status file so the dialogs are not shown again
    try:
        os.remove(UPDATE_STATUS_FILE)
    except Exception:
        pass


def play_intro():
    """Play the intro video if it exists and hasn't been played this boot."""
    if os.path.exists(FLAG_FILE):
        return
    if not os.path.exists(INTRO_PATH):
        xbmc.log("Akasha Splash: intro file not found at " + INTRO_PATH, xbmc.LOGWARNING)
        return

    # Mark as played for this boot session (/tmp is cleared on reboot)
    open(FLAG_FILE, "w").close()

    # Wait for Kodi to fully initialize
    monitor.waitForAbort(2)

    xbmc.log("Akasha Splash: playing intro video", xbmc.LOGINFO)

    # Start playback
    player = xbmc.Player()
    player.play(INTRO_PATH, windowed=False)

    # Wait for playback to actually start
    xbmc.sleep(500)

    # Force switch to fullscreen video view
    for _ in range(10):
        if player.isPlayingVideo():
            xbmc.executebuiltin("Action(FullScreen)")
            xbmc.sleep(200)
            xbmc.executebuiltin("Action(FullScreen)")
            break
        xbmc.sleep(200)

    # Wait for playback to finish or be interrupted
    while player.isPlaying() and not monitor.abortRequested():
        xbmc.sleep(200)

    xbmc.log("Akasha Splash: intro finished", xbmc.LOGINFO)


show_update_success()
play_intro()
