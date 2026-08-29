#!/usr/bin/env python3
"""Akasha Sleep — TV standby + wake-on-input.

Puts the TV in standby via CEC, turns off HDMI output to save power, then
waits 5 seconds before monitoring input devices (remote, keyboard, gamepad,
mouse). Any input event wakes the system: HDMI is turned back on and a CEC
wake sequence is sent to the TV.
"""
import os
import select
import struct
import subprocess
import sys
import time

CEC_DEVICE = '/dev/cec0'
CEC_DISABLED_FILE = '/storage/.config/akasha-os/CEC_DISABLED'
DISPLAY_ID = 0  # HDMI 0
TIMEOUT_BEFORE_WAKE = 5  # seconds


def _run(cmd, timeout=10):
    try:
        subprocess.run(cmd, shell=True, timeout=timeout, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _cec_setup():
    """Configure the CEC adapter as a playback device so the TV listens."""
    if os.path.exists(CEC_DISABLED_FILE):
        return False
    _run('cec-ctl -d0 --phys-addr 1.0.0.0 --osd-name Akasha '
         '--vendor-id 0x000c03 --playback --allow-unreg-fallback')
    time.sleep(0.5)
    _run('cec-ctl -d0 --from 4 --report-physical-addr '
         'phys-addr=1.0.0.0,prim-devtype=4 --raw-msg')
    time.sleep(0.5)
    _run('cec-ctl -d0 --from 4 --device-vendor-id '
         'vendor-id=0x000c03 --raw-msg')
    time.sleep(0.5)
    return True


def tv_standby():
    """Send CEC standby and turn off HDMI output."""
    if _cec_setup():
        _run('cec-ctl -d0 --from 4 --to 0 --standby --raw-msg')
        time.sleep(1)
    # Turn off HDMI output to reduce power/noise.
    _run('vcgencmd display_power {} 0'.format(DISPLAY_ID))


def tv_wake():
    """Turn HDMI back on and send CEC wake/active-source."""
    _run('vcgencmd display_power {} 1'.format(DISPLAY_ID))
    time.sleep(0.5)
    if _cec_setup():
        # Image View On (opcode 0x04) wakes most TVs, followed by Active Source.
        _run('cec-ctl -d0 --from 4 --to 0 --custom-command cmd=0x04')
        time.sleep(0.5)
        _run('cec-ctl -d0 --from 4 --active-source phys-addr=1.0.0.0 --raw-msg')


def _open_input_devices():
    """Open all input event devices in non-blocking mode."""
    fds = []
    for dev in sorted(os.listdir('/dev/input')):
        if not dev.startswith('event'):
            continue
        path = os.path.join('/dev/input', dev)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            fds.append(fd)
        except Exception:
            pass
    return fds


def _wait_for_input(fds):
    """Block until an input event is received on any device."""
    event_format = struct.Struct('llHHi')
    while True:
        try:
            ready, _, _ = select.select(fds, [], [], None)
        except (OSError, InterruptedError):
            continue
        for fd in ready:
            try:
                data = os.read(fd, event_format.size)
            except (OSError, BlockingIOError):
                continue
            if len(data) != event_format.size:
                continue
            _, _, ev_type, _, _ = event_format.unpack(data)
            # EV_SYN (0x00) is not a real user input; ignore it.
            if ev_type != 0x00:
                return


def main():
    try:
        # 1. Standby TV and reduce power.
        tv_standby()
        # 2. Wait for the TV to settle and avoid accidental wake events.
        time.sleep(TIMEOUT_BEFORE_WAKE)
        # 3. Monitor input devices.
        fds = _open_input_devices()
        if not fds:
            # No input devices; just sleep a while and then wake.
            time.sleep(30)
            tv_wake()
            return
        try:
            _wait_for_input(fds)
        finally:
            for fd in fds:
                try:
                    os.close(fd)
                except Exception:
                    pass
        # 4. Wake the TV and exit.
        tv_wake()
    except Exception as e:
        sys.stderr.write('Akasha Sleep error: {}\n'.format(e))
        # Try to restore display anyway.
        tv_wake()


if __name__ == '__main__':
    main()
