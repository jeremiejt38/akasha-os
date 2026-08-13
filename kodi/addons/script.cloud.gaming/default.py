import xbmc
import xbmcgui
import subprocess
import os

SERVICES = [
    ('GeForce NOW', 'https://play.geforcenow.com'),
    ('Xbox Cloud Gaming', 'https://xbox.com/play'),
    ('Amazon Luna', 'https://luna.amazon.com'),
    ('Google Stadia (Boosteroid)', 'https://cloud.boosteroid.com'),
]

def main():
    dialog = xbmcgui.Dialog()
    labels = [s[0] for s in SERVICES]
    choice = dialog.select('Cloud Gaming', labels)
    
    if choice < 0:
        return
    
    name, url = SERVICES[choice]
    
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
