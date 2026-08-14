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

INTRO_PATH = "/storage/.kodi/media/splash-intro.mp4"
FLAG_FILE = "/tmp/.akasha-intro-played"

addon = xbmcaddon.Addon()
monitor = xbmc.Monitor()


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


play_intro()
