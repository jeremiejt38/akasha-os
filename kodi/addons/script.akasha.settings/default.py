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

AMBIENT_ADDON_ID = 'script.akasha.ambient'

def get_ambient_enabled():
    try:
        return ADDON.getSetting('ambient.enabled').lower() == 'true'
    except:
        return True

def set_ambient_enabled(enabled):
    ADDON.setSetting('ambient.enabled', 'true' if enabled else 'false')

def _ambient_addon():
    return xbmcaddon.Addon(AMBIENT_ADDON_ID)

def get_ambient_setting(setting_id, default=''):
    try:
        value = _ambient_addon().getSetting(setting_id)
        return value if value != '' else default
    except:
        return default

def set_ambient_setting(setting_id, value):
    try:
        _ambient_addon().setSetting(setting_id, str(value))
    except:
        pass

def get_ambient_content_path():
    return get_ambient_setting('content_path', '/storage/ambient/photos')

def set_ambient_content_path():
    current = get_ambient_content_path()
    new_path = xbmcgui.Dialog().browse(0, 'Dossier de contenu du Mode Ambiant', 'files', '', False, False, current)
    if new_path:
        set_ambient_setting('content_path', new_path)
        xbmcgui.Dialog().notification('Akasha', 'Dossier Mode Ambiant mis a jour', xbmcgui.NOTIFICATION_INFO, 2000)

def get_ambient_minutes(setting_id, default):
    try:
        return int(get_ambient_setting(setting_id, str(default)))
    except (TypeError, ValueError):
        return default

def pick_ambient_minutes(title, setting_id, default, values):
    current = get_ambient_minutes(setting_id, default)
    labels = ['{} min'.format(v) for v in values]
    sel = xbmcgui.Dialog().select(title, labels, preselect=values.index(current) if current in values else 0)
    if sel >= 0:
        set_ambient_setting(setting_id, values[sel])
        xbmcgui.Dialog().notification('Akasha', '{}: {} min'.format(title, values[sel]), xbmcgui.NOTIFICATION_INFO, 2000)

def get_ambient_weather_enabled():
    return get_ambient_setting('weather_enabled', 'true').lower() == 'true'

def toggle_ambient_weather():
    new_state = not get_ambient_weather_enabled()
    set_ambient_setting('weather_enabled', 'true' if new_state else 'false')
    label = 'Activee' if new_state else 'Desactivee'
    xbmcgui.Dialog().notification('Akasha', 'Meteo Mode Ambiant: {}'.format(label), xbmcgui.NOTIFICATION_INFO, 2000)

def set_ambient_weather_city():
    current_city = get_ambient_setting('weather_city', 'Paris')
    new_city = xbmcgui.Dialog().input('Ville pour la meteo du Mode Ambiant', current_city, type=xbmcgui.INPUT_ALPHANUM)
    if new_city:
        set_ambient_setting('weather_city', new_city)
        xbmcgui.Dialog().notification('Akasha', 'Ville meteo: {}'.format(new_city), xbmcgui.NOTIFICATION_INFO, 2000)

def set_ambient_weather_coords():
    current_lat = get_ambient_setting('weather_latitude', '48.8566')
    current_lon = get_ambient_setting('weather_longitude', '2.3522')
    new_lat = xbmcgui.Dialog().numeric(0, 'Latitude (ville meteo)', str(current_lat))
    if new_lat == '':
        return
    new_lon = xbmcgui.Dialog().numeric(0, 'Longitude (ville meteo)', str(current_lon))
    if new_lon == '':
        return
    set_ambient_setting('weather_latitude', new_lat)
    set_ambient_setting('weather_longitude', new_lon)
    xbmcgui.Dialog().notification('Akasha', 'Coordonnees meteo mises a jour', xbmcgui.NOTIFICATION_INFO, 2000)

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

    old_version = status.get('local_version', 'Inconnue')
    new_version = status.get('remote_version', 'Inconnue')
    changelog = status.get('changelog', '')

    while True:
        choice = dialog.yesnocustom(
            'Akasha OS - Mise a jour',
            'Une nouvelle version est disponible.\n\n'
            '{} -> {}\n\n'
            'Attention : ne pas eteindre le systeme pendant la mise a jour.'.format(old_version, new_version),
            'Changelog',
            nolabel='Ignorer',
            yeslabel='[B][COLOR blue]Mettre a jour[/COLOR][/B]',
            defaultbutton=xbmcgui.DLG_YESNO_YES_BTN
        )

        if choice == 2:
            if changelog:
                xbmcgui.Dialog().ok(
                    'Akasha OS - Changelog v{}'.format(new_version),
                    changelog[:2000]
                )
            else:
                xbmcgui.Dialog().ok('Akasha OS - Changelog', 'Aucun changelog disponible.')
            continue

        if choice == 1:
            apply_update(status)
            return

        # choice == 0 or -1 -> cancel
        return

def apply_update(status):
    """Run the updater with a progress dialog, then reboot."""
    updater = '/storage/.kodi/scripts/update-akasha-os.py'
    progress = xbmcgui.DialogProgress()
    progress.create('Akasha OS - Mise a jour', 'Preparation...')

    proc = subprocess.Popen(
        ['python3', updater],
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
        return

    old_version = status.get('local_version', 'Inconnue')
    new_version = status.get('remote_version', 'Inconnue')
    changelog = status.get('changelog', '')

    # Persist update info so the startup service can show it after reboot
    try:
        import json as _json
        os.makedirs('/storage/.config/akasha-os', exist_ok=True)
        with open('/storage/.config/akasha-os/update-status.json', 'w') as f:
            _json.dump({
                'old_version': old_version,
                'new_version': new_version,
                'changelog': changelog
            }, f)
    except Exception:
        pass

    # Brief "Reboot in progress" progress; the post-reboot success dialog
    # will be shown by the splash service on the next boot.
    reboot_progress = xbmcgui.DialogProgress()
    reboot_progress.create('Akasha OS - Redemarrage', 'Redemarrage en cours, veuillez patienter...')
    for i in range(3, 0, -1):
        reboot_progress.update(int((4 - i) * 33), 'Redemarrage en cours...')
        xbmc.sleep(1000)
    reboot_progress.close()

    # Trigger reboot from the UI so the user sees the whole sequence
    subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)

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

def _toggle_overlay():
    overlay_enabled = ADDON.getSetting('overlay.enabled').lower() == 'true'
    new_state = 'false' if overlay_enabled else 'true'
    ADDON.setSetting('overlay.enabled', new_state)
    if new_state == 'true':
        xbmc.executebuiltin('Skin.SetBool(akasha_overlay)')
        xbmcgui.Dialog().notification('Akasha', 'Overlay systeme active', xbmcgui.NOTIFICATION_INFO, 2000)
    else:
        xbmc.executebuiltin('Skin.Reset(akasha_overlay)')
        xbmcgui.Dialog().notification('Akasha', 'Overlay systeme desactive', xbmcgui.NOTIFICATION_INFO, 2000)

def _toggle_ambient_enabled():
    ambient_enabled = get_ambient_enabled()
    set_ambient_enabled(not ambient_enabled)
    new_label = 'Active' if not ambient_enabled else 'Desactive'
    xbmcgui.Dialog().notification('Akasha', 'Mode Ambiant: {}'.format(new_label), xbmcgui.NOTIFICATION_INFO, 2000)

def _pick_shutdown_time():
    values = ['Desactive', '15 min', '30 min', '45 min', '60 min', '90 min', '120 min']
    int_values = [0, 15, 30, 45, 60, 90, 120]
    sel = xbmcgui.Dialog().select('Delai extinction automatique', values)
    if sel >= 0:
        set_shutdown_time(int_values[sel])
        set_shutdown_state(0)
        xbmcgui.Dialog().notification('Akasha', 'Extinction auto: {}'.format(values[sel]), xbmcgui.NOTIFICATION_INFO, 2000)

def _pick_screensaver_time():
    values = ['1 min', '3 min', '5 min', '10 min', '15 min', '20 min', '30 min']
    int_values = [1, 3, 5, 10, 15, 20, 30]
    sel = xbmcgui.Dialog().select('Delai ecran de veille', values)
    if sel >= 0:
        set_screensaver_time(int_values[sel])
        xbmcgui.Dialog().notification('Akasha', 'Screensaver: {}'.format(values[sel]), xbmcgui.NOTIFICATION_INFO, 2000)

def _force_shutdown_state():
    set_shutdown_state(0)
    xbmcgui.Dialog().notification('Akasha', 'Mode Shutdown + CEC active', xbmcgui.NOTIFICATION_INFO, 2000)

def _restart_kodi():
    ok = xbmcgui.Dialog().yesno('Akasha', 'Redemarrer Kodi ?')
    if ok:
        # Show reboot splash in ExecStartPre when Kodi restarts
        open('/tmp/.kodi-restart', 'w').close()
        subprocess.Popen(['systemctl', 'restart', 'kodi'], start_new_session=True)

def _restart_system():
    ok = xbmcgui.Dialog().yesno('Akasha', 'Redemarrer le systeme ?')
    if ok:
        # Show the reboot splash immediately before Kodi starts to tear down.
        # The matching systemd service will skip if the same image was shown recently.
        subprocess.run(['/storage/.kodi/scripts/show-splash.sh', '/storage/.kodi/media/splash-reboot.png'])
        subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)

def _shutdown_system():
    ok = xbmcgui.Dialog().yesno('Akasha', 'Eteindre le systeme ?\n(La TV sera aussi eteinte via CEC)')
    if ok:
        # Show the shutdown splash and turn the TV off via CEC before the system
        # shuts down. The matching systemd service will skip if already shown.
        subprocess.run(['/storage/.kodi/scripts/show-splash.sh', '/storage/.kodi/media/splash-shutdown.png', '1'])
        subprocess.Popen(['systemctl', 'poweroff'], start_new_session=True)

def main():
    while True:
        temp = get_cpu_temp()
        shutdown_min = get_shutdown_time()
        screensaver_min = get_screensaver_time()
        version = get_akasha_version()

        overlay_label = 'Active' if ADDON.getSetting('overlay.enabled').lower() == 'true' else 'Desactive'
        ambient_label = 'Active' if get_ambient_enabled() else 'Desactive'
        weather_label = 'Activee' if get_ambient_weather_enabled() else 'Desactivee'

        # (label, action) pairs; entries with action=None are section headers
        # and cannot be selected as a valid handler (guarded below).
        entries = [
            ('[B]--- Mise a jour ---[/B]', None),
            ('  Verifier / Mettre a jour Akasha OS (v{})'.format(version), show_update_dialog),
            ('[B]--- Infos Systeme ---[/B]', None),
            ('  Voir les infos systeme (CPU {}C)'.format(temp), show_system_info),
            ('  Overlay systeme : {}'.format(overlay_label), _toggle_overlay),
            ('[B]--- Mode Ambiant ---[/B]', None),
            ('  Mode Ambiant (ecran de veille) : {}'.format(ambient_label), _toggle_ambient_enabled),
            ('  Delai avant activation : {} min'.format(get_ambient_minutes('inactivity_timeout_minutes', 5)),
             lambda: pick_ambient_minutes('Delai avant activation', 'inactivity_timeout_minutes', 5, [1, 2, 3, 5, 10, 15, 30])),
            ('  Dossier de contenu : {}'.format(get_ambient_content_path()), set_ambient_content_path),
            ('  Delai avant assombrissement : {} min'.format(get_ambient_minutes('dim_after_minutes', 2)),
             lambda: pick_ambient_minutes('Delai avant assombrissement', 'dim_after_minutes', 2, [1, 2, 3, 5, 10])),
            ('  Delai avant veille complete : {} min'.format(get_ambient_minutes('sleep_after_minutes', 30)),
             lambda: pick_ambient_minutes('Delai avant veille complete', 'sleep_after_minutes', 30, [5, 10, 15, 30, 45, 60, 90])),
            ('  Meteo (Mode Ambiant) : {}'.format(weather_label), toggle_ambient_weather),
            ('  Ville (meteo Mode Ambiant) : {}'.format(get_ambient_setting('weather_city', 'Paris')), set_ambient_weather_city),
            ('  Coordonnees (meteo Mode Ambiant)...', set_ambient_weather_coords),
            ('[B]--- Veille & Extinction ---[/B]', None),
            ('  Delai extinction auto : {} min'.format(shutdown_min), _pick_shutdown_time),
            ('  Delai ecran de veille : {} min'.format(screensaver_min), _pick_screensaver_time),
            ('  Mode extinction : Shutdown + CEC (eteint la TV)', _force_shutdown_state),
            ('[B]--- Materiel ---[/B]', None),
            ('  Tester le ventilateur', test_fan),
            ('  Tester CEC (eteindre la TV)', test_cec_standby),
            ('[B]--- Actions ---[/B]', None),
            ('  Redemarrer Kodi', _restart_kodi),
            ('  Redemarrer le systeme', _restart_system),
            ('  Eteindre (shutdown + TV off)', _shutdown_system),
        ]

        options = [label for label, _ in entries]
        choice = xbmcgui.Dialog().select('Akasha Settings', options, useDetails=False)

        if choice < 0:
            break
        action = entries[choice][1]
        if action is not None:
            action()

if __name__ == '__main__':
    main()
