"""Akasha Voice -- entry point.

This script is the target of RunScript() calls and, in the future, of the
speech-to-text daemon. It receives a recognized phrase and executes the
corresponding Kodi/Akasha action.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon('script.akasha.voice')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(os.path.join(ADDON_PATH, 'resources', 'lib'))

from voice_handler import handle  # noqa: E402


def main():
    phrase = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    if not phrase:
        xbmc.log('Akasha Voice: no phrase provided', xbmc.LOGWARNING)
        return
    action = handle(phrase)
    if action:
        xbmc.log('Akasha Voice: "{}" -> {}'.format(phrase, action), xbmc.LOGINFO)
        xbmc.executebuiltin(action)
    else:
        xbmc.log('Akasha Voice: unrecognized phrase "{}"'.format(phrase), xbmc.LOGWARNING)


if __name__ == '__main__':
    main()
