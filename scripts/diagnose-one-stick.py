#!/usr/bin/env python3
"""Diagnostic long (60s) pour un seul joystick.

Affiche en temps reel les deux axes du stick choisi, puis un rapport final.
"""
import os
import struct
import fcntl
import time
import threading
import select
import sys

JSIOCGAXES = 0x80016a11
JSIOCGBUTTONS = 0x80016a12

def JSIOCGNAME(l):
    return (2 << 30) | (l << 16) | (0x6a << 8) | 0x13


def find_wireless_joystick():
    for dev in ["/dev/input/js0", "/dev/input/js1", "/dev/input/js2", "/dev/input/js3"]:
        if not os.path.exists(dev):
            continue
        try:
            with open(dev, "rb") as f:
                name = fcntl.ioctl(f, JSIOCGNAME(128), b" " * 128).decode(
                    errors="ignore"
                ).strip("\x00").strip()
                axes = struct.unpack("B", fcntl.ioctl(f, JSIOCGAXES, b"\x00"))[0]
                btns = struct.unpack("B", fcntl.ioctl(f, JSIOCGBUTTONS, b"\x00"))[0]
                print("  {} -> '{}' | axes={} buttons={}".format(dev, name, axes, btns))
                if axes >= 4 and ("Wireless" in name or "Bluetooth" in name.lower()):
                    return dev, name, axes
        except Exception:
            pass
    # fallback: most axes
    best = None
    for dev in ["/dev/input/js0", "/dev/input/js1", "/dev/input/js2", "/dev/input/js3"]:
        if os.path.exists(dev):
            try:
                with open(dev, "rb") as f:
                    axes = struct.unpack("B", fcntl.ioctl(f, JSIOCGAXES, b"\x00"))[0]
                    if best is None or axes > best[2]:
                        best = (dev, "", axes)
            except Exception:
                pass
    return best


def read_loop(fd, stop, samples):
    while not stop.is_set():
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            continue
        try:
            data = os.read(fd, 8)
        except OSError:
            break
        if len(data) < 8:
            continue
        t, value, typ, number = struct.unpack("<IhBB", data[:8])
        if (typ & 0x7f) == 0x02:
            samples.append((time.time(), number, value))


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("left", "right"):
        print("Usage: python3 diagnose-one-stick.py <left|right>")
        sys.exit(1)

    stick = sys.argv[1]
    label = "JOY GAUCHE" if stick == "left" else "JOY DROIT"
    print("\n=== Diagnostic 60s : {} ===\n".format(label))

    dev, name, naxes = find_wireless_joystick()
    if not dev:
        print("Joystick non trouve.")
        sys.exit(1)
    print("Selectionne: {}\n".format(dev))

    fd = os.open(dev, os.O_RDONLY)
    stop = threading.Event()
    samples = []
    t = threading.Thread(target=read_loop, args=(fd, stop, samples))
    t.daemon = True
    t.start()

    print("Preparation... 3s")
    time.sleep(3)

    print("[1/5] 10s - NE TOUCHE A RIEN (position centree)")
    time.sleep(10)
    print("[2/5] 15s - {} : cercles complets (lentement)".format(label))
    time.sleep(15)
    print("[3/5] 15s - {} : haut, bas, gauche, droite, chaque extremite".format(label))
    time.sleep(15)
    print("[4/5] 10s - {} : RELACHER COMPLETEMENT".format(label))
    time.sleep(10)
    print("[5/5] 10s - NE TOUCHE A RIEN (verif centre)")
    time.sleep(10)

    stop.set()
    t.join(timeout=2)
    os.close(fd)

    # Auto-detect the two most active axes for this stick
    stats = {}
    for ts, num, val in samples:
        if num not in stats:
            stats[num] = {"min": val, "max": val, "last": val, "count": 0, "sum": 0}
        s = stats[num]
        s["min"] = min(s["min"], val)
        s["max"] = max(s["max"], val)
        s["last"] = val
        s["count"] += 1
        s["sum"] += val

    # Top 2 axes by range
    top = sorted(stats.items(), key=lambda x: x[1]["max"] - x[1]["min"], reverse=True)[:2]

    print("\n=== RAPPORT FINAL : {} ===".format(label))
    print("Axes les plus actifs : {}".format(" / ".join(["Axe {}".format(n) for n, _ in top])))
    print()
    for num, s in top:
        rng = s["max"] - s["min"]
        avg = int(s["sum"] / s["count"]) if s["count"] else 0
        print("Axe {}:  min={:<7}  max={:<7}  plage={:<7}  moy={:<7}  dernier={:<7}  echantillons={}".format(
            num, s["min"], s["max"], rng, avg, s["last"], s["count"]))

    xnum, xs = top[0] if len(top) > 0 else (None, None)
    ynum, ys = top[1] if len(top) > 1 else (None, None)

    if xs and ys:
        x_range = xs["max"] - xs["min"]
        y_range = ys["max"] - ys["min"]
        x_center = abs(xs["last"]) < 3000
        y_center = abs(ys["last"]) < 3000
        print()
        if x_range < 60000:
            print("ALERTE Axe X : plage reduite ({})".format(x_range))
        if y_range < 60000:
            print("ALERTE Axe Y : plage reduite ({})".format(y_range))
        if not x_center:
            print("ALERTE Axe X : ne revient pas au centre (dernier={})".format(xs["last"]))
        if not y_center:
            print("ALERTE Axe Y : ne revient pas au centre (dernier={})".format(ys["last"]))
        if x_range >= 60000 and y_range >= 60000 and x_center and y_center:
            print("OK : plage et retour au centre corrects.")


if __name__ == "__main__":
    main()