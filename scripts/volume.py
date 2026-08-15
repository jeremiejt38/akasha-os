#!/usr/bin/env python3
"""Volume step helper for gamepad bumpers.

- 1er appui sur LB/RB : -/+ 5 %
- Maintien : -/+ 1 % a chaque appel repete (environ 10-20/s selon Kodi)
- Joystick droit desactive pour le volume
"""
import json
import os
import sys
import time

try:
    import xbmc
except Exception as e:
    with open('/tmp/volume_debug.log', 'a') as f:
        f.write('xbmc import error: {}\n'.format(e))
    sys.exit(0)

LOCK = "/tmp/volume_bumper.lock"
FIRST_STEP = 5
HOLD_STEP = 1
HOLD_INTERVAL = 0.08   # autorise un nouveau pas toutes les 80 ms
HOLD_TIMEOUT = 2.0     # un appui moins de 2s apres le precedent = maintien


def get_volume():
    rpc = {
        "jsonrpc": "2.0",
        "method": "Application.GetProperties",
        "params": {"properties": ["volume"]},
        "id": 1,
    }
    try:
        resp = json.loads(xbmc.executeJSONRPC(json.dumps(rpc)))
        return resp.get("result", {}).get("volume", 50)
    except Exception:
        return 50


def set_volume(vol):
    xbmc.executebuiltin("SetVolume({},showvolumebar)".format(int(vol)))


def main():
    direction = sys.argv[1] if len(sys.argv) > 1 else "up"
    now = time.time()

    last_dir = ""
    last_ts = 0.0
    try:
        with open(LOCK, "r") as f:
            parts = f.read().strip().split(",")
            if len(parts) == 2:
                last_ts = float(parts[0])
                last_dir = parts[1]
    except (IOError, ValueError):
        pass

    is_hold = (direction == last_dir and now - last_ts < HOLD_TIMEOUT)

    if is_hold:
        if now - last_ts < HOLD_INTERVAL:
            return
        step = HOLD_STEP
    else:
        step = FIRST_STEP

    with open(LOCK, "w") as f:
        f.write("{},{}".format(now, direction))

    vol = get_volume()
    if direction == "up":
        vol = min(100, vol + step)
    else:
        vol = max(0, vol - step)

    set_volume(vol)

    with open('/tmp/volume_debug.log', 'a') as f:
        f.write('{} -> vol={}\n'.format(direction, vol))


if __name__ == "__main__":
    main()