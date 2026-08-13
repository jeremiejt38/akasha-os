"""Akasha OS — Boot intro video.

Plays the splash intro video once when Kodi starts, then lets the
Home screen appear normally. The video can be skipped by pressing
any button on the remote/controller.
"""
import xbmc
import xbmcgui
import os

INTRO_PATH = "/storage/.kodi/media/splash-intro.mp4"
FLAG_FILE = "/tmp/.akasha-intro-played"


def play_intro():
    """Play the intro video if it exists and hasn't been played this boot."""
    if os.path.exists(FLAG_FILE):
        return
    if not os.path.exists(INTRO_PATH):
        return

    # Mark as played for this boot session
    open(FLAG_FILE, "w").close()

    # Play fullscreen
    xbmc.Player().play(INTRO_PATH, windowed=False)

    # Wait for playback to finish or be interrupted
    xbmc.sleep(500)
    while xbmc.Player().isPlaying():
        xbmc.sleep(200)


if __name__ == "__main__":
    play_intro()
else:
    play_intro()
