import os
import subprocess
import sys

import xbmc
import xbmcaddon
import xbmcgui

sys.path.insert(0, os.path.dirname(__file__))
from cloud_gaming_filter import filter_services  # noqa: E402

SERVICES = [
    ('GeForce NOW', 'https://play.geforcenow.com'),
    ('Xbox Cloud Gaming', 'https://xbox.com/play'),
    ('Amazon Luna', 'https://luna.amazon.com'),
    ('Google Stadia (Boosteroid)', 'https://cloud.boosteroid.com'),
]


def _preferred_services():
    """Whatever the Quick Start wizard's Cloud Gaming step (plan 3aba4284)
    had the user pre-select, if any -- read directly from
    script.akasha.aura's own addon setting (cross-addon settings reads
    are supported, unlike cross-addon Python imports)."""
    try:
        raw = xbmcaddon.Addon('script.akasha.aura').getSetting(
            'quickstart.cloud_gaming_services')
    except Exception:
        raw = ''
    return filter_services(SERVICES, raw)


def main():
    dialog = xbmcgui.Dialog()
    services = _preferred_services()
    labels = [s[0] for s in services]
    choice = dialog.select('Cloud Gaming', labels)
    
    if choice < 0:
        return
    
    name, url = services[choice]
    
    ok = dialog.yesno(
        'Cloud Gaming',
        'Lancer {} ?\n\nKodi sera arrete pendant la session.\n'
        'Pour revenir a Kodi : Alt+F4 (clavier) ou maintenir le bouton '
        'Guide/Xbox de la manette pendant 5 secondes.'.format(name)
    )
    
    if ok:
        # Lancer via systemd-run pour detacher launch.sh du cgroup de kodi.service :
        # kodi.service a KillMode=control-group, donc si launch.sh restait dans ce
        # cgroup, le "systemctl stop kodi" qu'il declenche le tuerait lui-meme
        # (et docker run avec) avant meme que Chromium ait pu demarrer.
        subprocess.Popen([
            'systemd-run', '--unit=cloud-gaming-launch', '--collect',
            '/bin/bash', '/storage/.kodi/scripts/cloud-gaming/launch.sh',
            url, name
        ])
        # Arrêter Kodi (le script le fait aussi mais on anticipe)
        xbmc.sleep(1000)

if __name__ == '__main__':
    main()
