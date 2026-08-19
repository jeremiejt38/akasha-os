"""Akasha Remote — script entry point for keymap-triggered actions.

Called by the remote keymap for volume and power actions. The background
service (service.py) handles battery monitoring; this thin entry point routes
button actions to the right destination based on the addon settings.
"""
import os
import sys

import xbmc
import xbmcaddon

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

import volume_router  # noqa: E402


def _handle_volume(action):
    addon = xbmcaddon.Addon()
    mode = volume_router.mode_from_setting(addon.getSetting('remote.volume_mode'))
    if mode == 'akasha':
        volume_router.route(action, mode, kodi_executebuiltin=xbmc.executebuiltin)
    elif mode == 'cec':
        volume_router.route(action, mode, cec_run=volume_router.run_cec_volume_command)
    elif mode == 'ir':
        xbmc.log('Akasha Remote: IR volume routing not implemented (no blaster hardware)',
                 xbmc.LOGWARNING)
    else:
        xbmc.log('Akasha Remote: unknown volume mode "{}"'.format(mode), xbmc.LOGWARNING)


def _handle_power():
    # Delegate to the existing Akasha sleep script, which sends CEC standby,
    # turns off HDMI output and waits for any input to wake back up.
    try:
        import subprocess  # noqa: E402
        subprocess.Popen(
            ['python3', '/storage/.kodi/scripts/akasha-sleep.py'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        xbmc.log('Akasha Remote: failed to start sleep script: {}'.format(e), xbmc.LOGERROR)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(0)
    action = sys.argv[1]
    if action in volume_router.ACTIONS:
        _handle_volume(action)
    elif action == 'power':
        _handle_power()
    else:
        xbmc.log('Akasha Remote: unhandled action "{}"'.format(action), xbmc.LOGWARNING)
