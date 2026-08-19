"""Akasha Remote — pure parsing of `bluetoothctl info <MAC>` text output.

No dependency on xbmc*/subprocess, so this module can be unit tested with
plain `python3 -m unittest`. `service.akasha.remote/service.py` is the thin
glue that actually shells out to `bluetoothctl` and feeds its stdout here.

LibreELEC's bluez ships neither `gatttool` nor Python BLE libraries
(bleak/bluepy) -- see docs/remote/decisions.md -- so `bluetoothctl info` is
the only practical way to read the standard BLE Battery Service (0x180F)
value without writing custom D-Bus/GATT code.
"""

import re

_BATTERY_RE = re.compile(r'Battery Percentage:\s*0x[0-9a-fA-F]+\s*\((\d+)\)')
_CONNECTED_RE = re.compile(r'^\s*Connected:\s*(yes|no)\s*$', re.MULTILINE)


def parse_battery_percentage(bluetoothctl_info_output):
    """Return the battery percentage (0-100) from `bluetoothctl info`
    output, or None if not present (e.g. remote disconnected -- bluez stops
    reporting a fresh reading once the BLE connection drops)."""
    match = _BATTERY_RE.search(bluetoothctl_info_output or '')
    if not match:
        return None
    value = int(match.group(1))
    if not (0 <= value <= 100):
        return None
    return value


def parse_connected(bluetoothctl_info_output):
    """Return True/False from the `Connected:` line, or None if absent."""
    match = _CONNECTED_RE.search(bluetoothctl_info_output or '')
    if not match:
        return None
    return match.group(1) == 'yes'
