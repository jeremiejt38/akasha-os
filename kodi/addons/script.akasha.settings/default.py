import xbmc
import xbmcgui
import xbmcaddon
import subprocess
import os
import json

ADDON = xbmcaddon.Addon()

def get_cpu_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except:
        return 0

def get_fan_status():
    try:
        result = subprocess.run(
            ['/storage/.kodi/addons/virtual.system-tools/bin/i2cget', '-y', '1', '0x1a'],
            capture_output=True, text=True, timeout=3
        )
        val = int(result.stdout.strip(), 16)
        if val == 0:
            return 'Arrete'
        return '{}%'.format(val)
    except:
        return 'Inconnu'

def get_wifi_status():
    try:
        result = subprocess.run(['connmanctl', 'services'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if '*AO' in line or '*AR' in line:
                name = line.split('  ')[0].replace('*AO ', '').replace('*AR ', '').strip()
                return 'Connecte: {}'.format(name)
        return 'Deconnecte'
    except:
        return 'Inconnu'

def get_shutdown_time():
    try:
        val = xbmc.getInfoLabel('Skin.String(ShutdownTime)')
    except:
        val = ''
    # Lire depuis guisettings
    try:
        result = subprocess.run(['grep', 'shutdowntime', '/storage/.kodi/userdata/guisettings.xml'],
                               capture_output=True, text=True)
        import re
        m = re.search(r'>(\d+)<', result.stdout)
        if m:
            return int(m.group(1))
    except:
        pass
    return 30

def set_shutdown_time(minutes):
    try:
        xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0',
            'method': 'Settings.SetSettingValue',
            'params': {'setting': 'powermanagement.shutdowntime', 'value': minutes},
            'id': 1
        }))
    except:
        pass

def set_shutdown_state(state):
    try:
        xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0',
            'method': 'Settings.SetSettingValue',
            'params': {'setting': 'powermanagement.shutdownstate', 'value': state},
            'id': 1
        }))
    except:
        pass

def get_screensaver_time():
    try:
        result = subprocess.run(['grep', 'screensaver.time', '/storage/.kodi/userdata/guisettings.xml'],
                               capture_output=True, text=True)
        import re
        m = re.search(r'>(\d+)<', result.stdout)
        if m:
            return int(m.group(1))
    except:
        pass
    return 5

def set_screensaver_time(minutes):
    try:
        xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0',
            'method': 'Settings.SetSettingValue',
            'params': {'setting': 'screensaver.time', 'value': minutes},
            'id': 1
        }))
    except:
        pass

def test_fan():
    dialog = xbmcgui.Dialog()
    dialog.notification('Akasha', 'Test ventilateur 50%...', xbmcgui.NOTIFICATION_INFO, 3000)
    subprocess.run(['/storage/.kodi/addons/virtual.system-tools/bin/i2cset', '-y', '1', '0x1a', '50'], timeout=3)
    xbmc.sleep(5000)
    subprocess.run(['/storage/.kodi/addons/virtual.system-tools/bin/i2cset', '-y', '1', '0x1a', '0'], timeout=3)
    dialog.notification('Akasha', 'Ventilateur arrete', xbmcgui.NOTIFICATION_INFO, 2000)

def test_cec_standby():
    dialog = xbmcgui.Dialog()
    ok = dialog.yesno('Akasha', 'Envoyer le signal CEC Standby a la TV ?\n(La TV va s\'eteindre)')
    if ok:
        subprocess.run(['/bin/bash', '/storage/.config/cec-standby.sh'], timeout=10)

def check_for_update():
    """Check for an Akasha OS update and return status dict or None."""
    updater = '/storage/.kodi/scripts/update-akasha-os.py'
    if not os.path.exists(updater):
        return {'status': 'error', 'message': 'Updater script not found'}

    dialog = xbmcgui.Dialog()
    dialog.notification('Akasha', 'Recherche de mise a jour...', xbmcgui.NOTIFICATION_INFO, 2000)

    result = subprocess.run(
        ['python3', updater, '--check'],
        capture_output=True,
        text=True,
        timeout=60
    )

    for line in reversed(result.stdout.splitlines()):
        if line.startswith('JSON '):
            try:
                return json.loads(line[5:])
            except:
                pass
    return {'status': 'error', 'message': 'Impossible de lire le resultat'}

def show_update_dialog():
    """Check, then optionally apply an Akasha OS update."""
    status = check_for_update()
    dialog = xbmcgui.Dialog()

    if status.get('status') == 'up_to_date':
        dialog.ok(
            'Akasha OS - Mise a jour',
            'Vous etes a jour.\nVersion actuelle : {}'.format(status.get('local_version', 'Inconnue'))
        )
        return

    if status.get('status') != 'update':
        dialog.ok('Akasha OS - Mise a jour', 'Erreur : {}'.format(status.get('message', 'Inconnue')))
        return

    changelog = status.get('changelog', '')[:800]
    msg = (
        'Nouvelle version disponible : {}\n'
        'Version actuelle : {}\n\n'
        'Changelog :\n{}\n\n'
        'Lancer la mise a jour ?'
    ).format(status.get('remote_version'), status.get('local_version'), changelog)

    if not dialog.yesno('Akasha OS - Mise a jour', msg):
        return

    apply_update()

def apply_update():
    """Run the updater with a progress dialog."""
    updater = '/storage/.kodi/scripts/update-akasha-os.py'
    progress = xbmcgui.DialogProgress()
    progress.create('Akasha OS - Mise a jour', 'Preparation...')

    proc = subprocess.Popen(
        ['python3', updater, '--reboot'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    pct = 0
    stage = 'Initialisation'
    while proc.poll() is None:
        line = proc.stdout.readline()
        if not line:
            xbmc.sleep(200)
            continue

        # Parse progress markers
        if line.startswith('### PROGRESS:'):
            try:
                pct = int(line.split(':', 1)[1].strip())
            except:
                pass
        elif line.startswith('### STAGE:'):
            stage = line.split(':', 1)[1].strip()
        elif line.startswith('### '):
            pass
        else:
            # Real log line; show last meaningful one
            if not line.startswith('[') and line.strip():
                stage = line.strip()[:60]

        progress.update(pct, 'Etape : {}'.format(stage))
        xbmc.sleep(50)

    # Drain remaining output
    for line in proc.stdout:
        pass

    progress.close()

    if proc.returncode != 0:
        xbmcgui.Dialog().ok('Akasha OS - Erreur', 'La mise a jour a echoue.\nVoir le log.')
    else:
        # Reboot is handled by the script, but if not this dialog will appear briefly
        xbmcgui.Dialog().ok('Akasha OS - Redemarrage', 'Mise a jour terminee.\nRedemarrage en cours...')

def get_akasha_version():
    try:
        with open('/storage/.config/akasha-os/VERSION') as f:
            return f.read().strip()
    except:
        return 'Inconnue'

def show_system_info():
    temp = get_cpu_temp()
    fan = get_fan_status()
    wifi = get_wifi_status()
    version = get_akasha_version()
    
    try:
        result = subprocess.run(['uptime', '-p'], capture_output=True, text=True, timeout=3)
        uptime_str = result.stdout.strip()
    except:
        uptime_str = 'Inconnu'
    
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=3)
        lines = result.stdout.strip().split('\n')
        mem_line = lines[1].split()
        mem_total = mem_line[1]
        mem_used = mem_line[2]
        mem_str = '{}/{}MB'.format(mem_used, mem_total)
    except:
        mem_str = 'Inconnu'
    
    try:
        result = subprocess.run(['cat', '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'],
                               capture_output=True, text=True, timeout=3)
        governor = result.stdout.strip()
    except:
        governor = 'Inconnu'
    
    try:
        result = subprocess.run(['cat', '/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'],
                               capture_output=True, text=True, timeout=3)
        freq = '{}MHz'.format(int(result.stdout.strip()) // 1000)
    except:
        freq = 'Inconnu'

    msg = (
        'Version Akasha OS : {}\n'
        'Temperature CPU : {}C\n'
        'Ventilateur : {}\n'
        'WiFi : {}\n'
        'Memoire : {}\n'
        'CPU : {} @ {}\n'
        'Uptime : {}'
    ).format(version, temp, fan, wifi, mem_str, governor, freq, uptime_str)

    xbmcgui.Dialog().textviewer('Akasha - Infos Systeme', msg)

def main():
    while True:
        temp = get_cpu_temp()
        shutdown_min = get_shutdown_time()
        screensaver_min = get_screensaver_time()
        
        version = get_akasha_version()

        options = [
            '[B]--- Mise a jour ---[/B]',
            '  Verifier / Mettre a jour Akasha OS (v{})'.format(version),
            '[B]--- Infos Systeme ---[/B]',
            '  Voir les infos systeme (CPU {}C)'.format(temp),
            '[B]--- Veille & Extinction ---[/B]',
            '  Delai extinction auto : {} min'.format(shutdown_min),
            '  Delai ecran de veille : {} min'.format(screensaver_min),
            '  Mode extinction : Shutdown + CEC (eteint la TV)',
            '[B]--- Materiel ---[/B]',
            '  Tester le ventilateur',
            '  Tester CEC (eteindre la TV)',
            '[B]--- Actions ---[/B]',
            '  Redemarrer Kodi',
            '  Redemarrer le systeme',
            '  Eteindre (shutdown + TV off)',
        ]
        
        dialog = xbmcgui.Dialog()
        choice = dialog.select('Akasha Settings', options, useDetails=False)
        
        if choice < 0:
            break
        elif choice == 1:
            show_update_dialog()
        elif choice == 3:
            show_system_info()
        elif choice == 5:
            # Changer délai extinction
            values = ['Desactive', '15 min', '30 min', '45 min', '60 min', '90 min', '120 min']
            int_values = [0, 15, 30, 45, 60, 90, 120]
            sel = dialog.select('Delai extinction automatique', values)
            if sel >= 0:
                set_shutdown_time(int_values[sel])
                set_shutdown_state(0)
                dialog.notification('Akasha', 'Extinction auto: {}'.format(values[sel]), xbmcgui.NOTIFICATION_INFO, 2000)
        elif choice == 6:
            # Changer délai screensaver
            values = ['1 min', '3 min', '5 min', '10 min', '15 min', '20 min', '30 min']
            int_values = [1, 3, 5, 10, 15, 20, 30]
            sel = dialog.select('Delai ecran de veille', values)
            if sel >= 0:
                set_screensaver_time(int_values[sel])
                dialog.notification('Akasha', 'Screensaver: {}'.format(values[sel]), xbmcgui.NOTIFICATION_INFO, 2000)
        elif choice == 7:
            # Forcer shutdown state
            set_shutdown_state(0)
            dialog.notification('Akasha', 'Mode Shutdown + CEC active', xbmcgui.NOTIFICATION_INFO, 2000)
        elif choice == 9:
            test_fan()
        elif choice == 10:
            test_cec_standby()
        elif choice == 12:
            ok = dialog.yesno('Akasha', 'Redemarrer Kodi ?')
            if ok:
                # Show reboot splash in ExecStartPre when Kodi restarts
                open('/tmp/.kodi-restart', 'w').close()
                subprocess.Popen(['systemctl', 'restart', 'kodi'], start_new_session=True)
        elif choice == 13:
            ok = dialog.yesno('Akasha', 'Redemarrer le systeme ?')
            if ok:
                # Show the reboot splash immediately before Kodi starts to tear down.
                # The matching systemd service will skip if the same image was shown recently.
                subprocess.run(['/storage/.kodi/scripts/show-splash.sh', '/storage/.kodi/media/splash-reboot.png'])
                subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)
        elif choice == 14:
            ok = dialog.yesno('Akasha', 'Eteindre le systeme ?\n(La TV sera aussi eteinte via CEC)')
            if ok:
                # Show the shutdown splash and turn the TV off via CEC before the system
                # shuts down. The matching systemd service will skip if already shown.
                subprocess.run(['/storage/.kodi/scripts/show-splash.sh', '/storage/.kodi/media/splash-shutdown.png', '1'])
                subprocess.Popen(['systemctl', 'poweroff'], start_new_session=True)

if __name__ == '__main__':
    main()
