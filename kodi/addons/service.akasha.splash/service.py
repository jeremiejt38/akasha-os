"""Akasha Splash — Boot intro video + OTA update check service.

Plays the splash intro video once when Kodi starts, then lets the
Home screen appear normally. The video can be skipped by pressing
any button on the remote/controller.

When the system is online, it also checks for an Akasha OS update and
offers to install it, show the changelog, or ignore it.

This is a Kodi service addon (replaces deprecated autoexec.py).
"""
import xbmc
import xbmcaddon
import xbmcgui
import os
import json
import subprocess
import time

INTRO_PATH = "/storage/.kodi/media/splash-intro.mp4"
FLAG_FILE = "/tmp/.akasha-intro-played"
UPDATE_STATUS_FILE = "/storage/.config/akasha-os/update-status.json"
UPDATE_IGNORED_FILE = "/storage/.config/akasha-os/update-ignored.json"
UPDATER = "/storage/.kodi/scripts/update-akasha-os.py"

addon = xbmcaddon.Addon()
monitor = xbmc.Monitor()


def _wait_for_network(timeout=90):
    """Wait until the device can reach GitHub, or timeout expires."""
    xbmc.log("Akasha Splash: waiting for network / update server", xbmc.LOGINFO)
    start = time.time()
    attempt = 0
    while time.time() - start < timeout and not monitor.abortRequested():
        attempt += 1
        xbmc.log("Akasha Splash: update check attempt {}".format(attempt), xbmc.LOGINFO)
        try:
            result = subprocess.run(
                ['python3', UPDATER, '--check'],
                capture_output=True, text=True, timeout=15
            )
            xbmc.log("Akasha Splash: updater returned code {}".format(result.returncode), xbmc.LOGINFO)
            for line in reversed(result.stdout.splitlines()):
                if line.startswith('JSON '):
                    xbmc.log("Akasha Splash: got update JSON", xbmc.LOGINFO)
                    return json.loads(line[5:])
            # If we got a JSON line, the network is up enough to reach GitHub.
            # If not (e.g. timeout), retry.
        except Exception as e:
            xbmc.log("Akasha Splash: updater exception {}".format(str(e)), xbmc.LOGERROR)
        xbmc.log("Akasha Splash: update check failed, retrying in 3s", xbmc.LOGINFO)
        monitor.waitForAbort(3)
    return None


def _is_ignored(version):
    try:
        if os.path.exists(UPDATE_IGNORED_FILE):
            with open(UPDATE_IGNORED_FILE, 'r') as f:
                ignored = json.load(f)
            return ignored.get('version') == version
    except Exception:
        pass
    return False


def _set_ignored(version):
    try:
        os.makedirs('/storage/.config/akasha-os', exist_ok=True)
        with open(UPDATE_IGNORED_FILE, 'w') as f:
            json.dump({'version': version}, f)
    except Exception:
        pass


def _apply_update(status):
    """Run the OTA updater from the startup service with a progress dialog."""
    progress = xbmcgui.DialogProgress()
    progress.create('Akasha OS - Mise a jour', 'Preparation...')

    proc = subprocess.Popen(
        ['python3', UPDATER],
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

        if line.startswith('### PROGRESS:'):
            try:
                pct = int(line.split(':', 1)[1].strip())
            except Exception:
                pass
        elif line.startswith('### STAGE:'):
            stage = line.split(':', 1)[1].strip()
        elif line.startswith('### '):
            pass
        else:
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
        os.makedirs('/storage/.config/akasha-os', exist_ok=True)
        with open(UPDATE_STATUS_FILE, 'w') as f:
            json.dump({
                'old_version': old_version,
                'new_version': new_version,
                'changelog': changelog
            }, f)
    except Exception:
        pass

    xbmcgui.Dialog().ok(
        'Akasha OS - Mise a jour terminee',
        'Mise a jour reussie.\n\n{} -> {}\n\n'
        'Le systeme va redemarrer pour appliquer les changements.'.format(old_version, new_version)
    )

    reboot_progress = xbmcgui.DialogProgress()
    reboot_progress.create('Akasha OS - Redemarrage', 'Redemarrage en cours, veuillez patienter...')
    for i in range(5, 0, -1):
        reboot_progress.update(int((6 - i) * 20), 'Redemarrage dans {}s...'.format(i))
        xbmc.sleep(1000)
    reboot_progress.close()

    subprocess.Popen(['systemctl', 'reboot'], start_new_session=True)


def check_for_updates_at_boot():
    """Check for updates once online and prompt the user if one is available."""
    xbmc.log("Akasha Splash: checking for updates at boot", xbmc.LOGINFO)

    # Wait a moment for the network stack and Kodi to settle
    xbmc.log("Akasha Splash: waiting 3s for Kodi/network to settle", xbmc.LOGINFO)
    monitor.waitForAbort(3)

    status = _wait_for_network(timeout=90)
    if not status:
        xbmc.log("Akasha Splash: could not reach update server (timeout)", xbmc.LOGWARNING)
        return

    xbmc.log("Akasha Splash: status={}, local={}, remote={}".format(
        status.get('status'), status.get('local_version'), status.get('remote_version')), xbmc.LOGINFO)

    if status.get('status') != 'update':
        xbmc.log("Akasha Splash: no update available", xbmc.LOGINFO)
        return

    new_version = status.get('remote_version', 'Inconnue')
    if _is_ignored(new_version):
        xbmc.log("Akasha Splash: update {} ignored by user".format(new_version), xbmc.LOGINFO)
        return

    dialog = xbmcgui.Dialog()
    old_version = status.get('local_version', 'Inconnue')
    changelog = status.get('changelog', '')

    heading = 'Akasha OS - Mise a jour'
    while True:
        choice = dialog.yesnocustom(
            heading,
            'Une nouvelle version est disponible.\n\n'
            '{} -> {}\n\n'
            'Que souhaitez-vous faire ?'.format(old_version, new_version),
            'Changelog',
            nolabel='Ignorer',
            yeslabel='[B][COLOR blue]Mettre a jour[/COLOR][/B]',
            defaultbutton=xbmcgui.DLG_YESNO_YES_BTN
        )

        if choice == 2:
            if changelog:
                dialog.textviewer(
                    'Akasha OS - Changelog v{}'.format(new_version),
                    changelog
                )
            else:
                dialog.ok('Akasha OS - Changelog', 'Aucun changelog disponible.')
            continue

        if choice == 1:
            _apply_update(status)
            return

        # choice == 0 (No / Ignorer), -1 (Back / escape), or any other
        _set_ignored(new_version)
        xbmc.log("Akasha Splash: update {} will be ignored".format(new_version), xbmc.LOGINFO)
        break


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


# Play the boot intro first so the video/audio are not delayed or
# overlapped by the update check dialogs. Update prompts appear after.
play_intro()
show_update_success()
check_for_updates_at_boot()