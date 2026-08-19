"""Akasha Remote — Bluetooth remote monitoring service.

Polls the paired remote's standard BLE Battery Service (0x180F) level via
`bluetoothctl info <mac>` (LibreELEC's bluez ships neither `gatttool` nor a
Python BLE library -- see docs/remote/decisions.md) and shows a Kodi
notification once when the battery drops below the configured threshold.

This is deliberately narrow in scope: see docs/remote/decisions.md for why
the remote's microphone, "find my remote" buzzer and IR blaster are NOT
handled here (undocumented proprietary Amazon BLE protocol, no automatic
GATT traffic observed), and why button-press timing (simple/long/double,
see script.akasha.aura's default.py) is handled inside Kodi's own Python
addon layer rather than by this service -- Kodi's SDL2 input backend holds
an exclusive EVIOCGRAB on the remote's HID device, so a separate process
reading /dev/input directly receives no events at all while Kodi is running
(confirmed empirically on the real device).
"""
import json
import os
import subprocess
import sys

import xbmc
import xbmcaddon

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

from battery_alert import BatteryAlertTracker  # noqa: E402
from bluetoothctl_parser import parse_battery_percentage, parse_connected  # noqa: E402

ADDON_ID = 'service.akasha.remote'
STATE_FILE = '/storage/.akasha/remote_state.json'
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_LOW_BATTERY_THRESHOLD = 15


def _bluetoothctl_info(mac_address):
    try:
        result = subprocess.run(
            ['bluetoothctl', 'info', mac_address],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return result.stdout
    except Exception as e:
        xbmc.log('Akasha Remote: bluetoothctl info failed: {}'.format(e), xbmc.LOGWARNING)
        return ''


def _write_state(percent, connected):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump({'battery_percent': percent, 'connected': connected}, f)
    except Exception as e:
        xbmc.log('Akasha Remote: could not write state file: {}'.format(e), xbmc.LOGWARNING)


def _notify_low_battery(percent):
    xbmc.executebuiltin(
        'Notification(Akasha, Batterie telecommande faible ({}%25), 5000)'.format(percent))


def _load_settings():
    addon = xbmcaddon.Addon(ADDON_ID)
    mac_address = addon.getSetting('remote.mac_address').strip()
    try:
        poll_interval = int(addon.getSetting('remote.poll_interval_seconds'))
    except (TypeError, ValueError):
        poll_interval = DEFAULT_POLL_INTERVAL_SECONDS
    try:
        low_threshold = int(addon.getSetting('remote.low_battery_threshold'))
    except (TypeError, ValueError):
        low_threshold = DEFAULT_LOW_BATTERY_THRESHOLD
    return mac_address, max(30, poll_interval), low_threshold


def main():
    monitor = xbmc.Monitor()
    mac_address, poll_interval, low_threshold = _load_settings()
    if not mac_address:
        xbmc.log('Akasha Remote: no remote.mac_address configured, service idle', xbmc.LOGINFO)
        return

    tracker = BatteryAlertTracker(low_threshold=low_threshold)

    # Give Kodi/bluetoothd a moment to finish starting up before the first check.
    if monitor.waitForAbort(10):
        return

    while not monitor.abortRequested():
        try:
            info = _bluetoothctl_info(mac_address)
            percent = parse_battery_percentage(info)
            connected = parse_connected(info)
            _write_state(percent, connected)
            if tracker.observe(percent):
                xbmc.log('Akasha Remote: low battery ({}%)'.format(percent), xbmc.LOGINFO)
                _notify_low_battery(percent)
        except Exception as e:
            xbmc.log('Akasha Remote: error in main loop: {}'.format(e), xbmc.LOGERROR)

        monitor.waitForAbort(poll_interval)


if __name__ == '__main__':
    main()
