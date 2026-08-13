#!/usr/bin/env python3
"""
Cloud Gaming - Guide button watchdog.

Surveille les manettes connectees (recherchees dynamiquement dans
/proc/bus/input/devices) et detecte un appui long (>= HOLD_SECONDS) sur le
bouton Guide/Xbox (BTN_MODE). Quand c'est le cas, force l'arret du conteneur
Docker de la session cloud gaming en cours, ce qui fait revenir a Kodi
(equivalent d'Alt+F4 au clavier, mais utilisable sans clavier).

Usage: guide_watchdog.py <nom_du_conteneur_docker>
"""
import glob
import select
import struct
import subprocess
import sys
import time

HOLD_SECONDS = 5
POLL_INTERVAL = 0.2

# struct input_event sur Linux 64 bits : { long tv_sec; long tv_usec; __u16 type; __u16 code; __s32 value; }
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

EV_KEY = 1
BTN_MODE = 0x13C  # 316, bouton Guide/Xbox


def find_gamepad_events():
    """Retourne la liste des /dev/input/eventN qui semblent etre des manettes."""
    try:
        with open("/proc/bus/input/devices") as f:
            content = f.read()
    except OSError:
        return []

    devices = []
    for block in content.split("\n\n"):
        if "N: Name=" not in block:
            continue
        name_line = next((l for l in block.splitlines() if l.startswith("N: Name=")), "")
        is_pad = any(k in name_line for k in ("X-Box", "Xbox", "Gamepad", "Controller", "gamepad"))
        if not is_pad:
            continue
        for line in block.splitlines():
            if line.startswith("H:"):
                for tok in line.split():
                    if tok.startswith("event"):
                        devices.append(f"/dev/input/{tok}")
    return devices


def stop_container(container):
    subprocess.run(["docker", "stop", container], check=False)


def main():
    if len(sys.argv) < 2:
        print("Usage: guide_watchdog.py <container_name>", file=sys.stderr)
        sys.exit(1)
    container = sys.argv[1]

    devices = find_gamepad_events()
    if not devices:
        # Pas de manette detectee, rien a surveiller
        return

    handles = []
    for path in devices:
        try:
            handles.append(open(path, "rb"))
        except OSError:
            continue

    if not handles:
        return

    press_start = None
    try:
        while True:
            ready, _, _ = select.select(handles, [], [], POLL_INTERVAL)
            for h in ready:
                data = h.read(EVENT_SIZE)
                if len(data) != EVENT_SIZE:
                    continue
                _, _, ev_type, code, value = struct.unpack(EVENT_FORMAT, data)
                if ev_type == EV_KEY and code == BTN_MODE:
                    if value == 1:  # pression
                        press_start = time.time()
                    elif value == 0:  # relachement
                        press_start = None

            if press_start is not None and (time.time() - press_start) >= HOLD_SECONDS:
                stop_container(container)
                return
    finally:
        for h in handles:
            try:
                h.close()
            except OSError:
                pass


if __name__ == "__main__":
    main()
