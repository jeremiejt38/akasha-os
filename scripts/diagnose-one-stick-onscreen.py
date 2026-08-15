#!/usr/bin/env python3
"""Diagnostic 60s d'un joystick avec instructions affichees sur l'ecran TV."""
import os
import struct
import fcntl
import time
import threading
import select
import sys
import subprocess

JSIOCGAXES = 0x80016a11
JSIOCGBUTTONS = 0x80016a12

def JSIOCGNAME(l):
    return (2 << 30) | (l << 16) | (0x6a << 8) | 0x13


def find_joystick():
    for dev in ["/dev/input/js0", "/dev/input/js1", "/dev/input/js2"]:
        if not os.path.exists(dev):
            continue
        try:
            with open(dev, "rb") as f:
                name = fcntl.ioctl(f, JSIOCGNAME(128), b" " * 128).decode(errors="ignore").strip("\x00").strip()
                axes = struct.unpack("B", fcntl.ioctl(f, JSIOCGAXES, b"\x00"))[0]
                if axes >= 4 and ("Wireless" in name or "Bluetooth" in name.lower() or "Xbox" in name):
                    return dev, name, axes
        except Exception:
            pass
    for dev in ["/dev/input/js0", "/dev/input/js1", "/dev/input/js2"]:
        if os.path.exists(dev):
            try:
                with open(dev, "rb") as f:
                    axes = struct.unpack("B", fcntl.ioctl(f, JSIOCGAXES, b"\x00"))[0]
                    if axes >= 4:
                        return dev, "", axes
            except Exception:
                pass
    return None, None, 0


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


def show_image(path):
    FFMPEG = "/storage/ffmpeg"
    if not os.path.exists(path) or not os.path.exists(FFMPEG):
        return
    subprocess.run([
        FFMPEG, "-y", "-i", path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-pix_fmt", "rgb565le", "-f", "fbdev", "/dev/fb0",
        "-an", "-loglevel", "warning"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def beep(high=True):
    f = "/tmp/joystick-cards/beep-high.wav" if high else "/tmp/joystick-cards/beep-low.wav"
    if os.path.exists(f):
        subprocess.Popen(["aplay", "-q", f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait(duration, label, state):
    deadline = time.time() + duration
    while time.time() < deadline:
        remaining = int(deadline - time.time())
        if remaining != state["last"]:
            print("  {} reste {}s".format(label, remaining))
            sys.stdout.flush()
            state["last"] = remaining
        time.sleep(0.2)
    state["last"] = -1


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("left", "right"):
        print("Usage: python3 diagnose-one-stick-onscreen.py <left|right>")
        sys.exit(1)

    stick = sys.argv[1]
    label = "JOYSTICK GAUCHE" if stick == "left" else "JOYSTICK DROIT"
    img_dir = "/tmp/joystick-cards"

    print("\n=== Diagnostic 60s : {} ===".format(label))
    dev, name, naxes = find_joystick()
    if not dev:
        print("Manette non trouvee.")
        sys.exit(1)
    print("\nSelectionne: {}".format(dev))

    fd = os.open(dev, os.O_RDONLY)
    stop = threading.Event()
    samples = []
    t = threading.Thread(target=read_loop, args=(fd, stop, samples))
    t.daemon = True
    t.start()

    state = {"last": -1}

    print("\nAttente 5s avant demarrage... (image affichee)")
    show_image(os.path.join(img_dir, "center.png"))
    time.sleep(5)

    # Phase 1: center
    beep(high=False)
    show_image(os.path.join(img_dir, "center.png"))
    print("\n[1/5] 10s - NE TOUCHE A RIEN")
    wait(10, "centre", state)

    # Phase 2: circles
    beep(high=True)
    img = os.path.join(img_dir, "{}_circles.png".format(stick))
    show_image(img)
    print("\n[2/5] 15s - {} : cercles complets".format(label))
    wait(15, "cercles", state)

    # Phase 3: corners
    img = os.path.join(img_dir, "{}_corners.png".format(stick))
    show_image(img)
    print("\n[3/5] 15s - {} : haut, bas, gauche, droite".format(label))
    wait(15, "coins", state)

    # Phase 4: release
    beep(high=True)
    img = os.path.join(img_dir, "{}_release.png".format(stick))
    show_image(img)
    print("\n[4/5] 10s - {} : RELACHER".format(label))
    wait(10, "relache", state)

    # Phase 5: verify center
    beep(high=False)
    show_image(os.path.join(img_dir, "center.png"))
    print("\n[5/5] 10s - NE TOUCHE A RIEN (verif)")
    wait(10, "verif centre", state)

    stop.set()
    t.join(timeout=2)
    os.close(fd)

    show_image(os.path.join(img_dir, "done.png"))
    beep(high=True)
    beep(high=False)

    # Analyze
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

    top = sorted(stats.items(), key=lambda x: x[1]["max"] - x[1]["min"], reverse=True)[:2]

    print("\n=== RAPPORT FINAL : {} ===".format(label))
    print("Axes les plus actifs : {}".format(" / ".join(["Axe {}".format(n) for n, _ in top])))
    for num, s in top:
        rng = s["max"] - s["min"]
        avg = int(s["sum"] / s["count"]) if s["count"] else 0
        print("Axe {}: min={:<7} max={:<7} plage={:<7} moy={:<7} dernier={:<7} echantillons={}".format(
            num, s["min"], s["max"], rng, avg, s["last"], s["count"]))

    if len(top) >= 2:
        xnum, xs = top[0]
        ynum, ys = top[1]
        x_range = xs["max"] - xs["min"]
        y_range = ys["max"] - ys["min"]
        x_center = abs(xs["last"]) < 3000
        y_center = abs(ys["last"]) < 3000
        print()
        if x_range < 60000:
            print("ALERTE Axe X (probablement {}): plage reduite ({})".format(xnum, x_range))
        if y_range < 60000:
            print("ALERTE Axe Y (probablement {}): plage reduite ({})".format(ynum, y_range))
        if not x_center:
            print("ALERTE Axe X (probablement {}): ne revient pas au centre (dernier={})".format(xnum, xs["last"]))
        if not y_center:
            print("ALERTE Axe Y (probablement {}): ne revient pas au centre (dernier={})".format(ynum, ys["last"]))
        if x_range >= 60000 and y_range >= 60000 and x_center and y_center:
            print("OK : plage et retour au centre corrects.")


if __name__ == "__main__":
    main()