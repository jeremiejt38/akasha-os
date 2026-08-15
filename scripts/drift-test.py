#!/usr/bin/env python3
"""Test de derive / ghost input sur 2 minutes.
La manette ne doit pas etre touchee. Le script affiche un message a l'ecran,
enregistre tous les axes et signale tout mouvement non demande.
"""
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


def find_wireless_joystick():
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


def main():
    print("\n=== Test de derive 2 minutes ===\n")
    dev, name, naxes = find_wireless_joystick()
    if not dev:
        print("Manette non trouvee.")
        sys.exit(1)
    print("Selectionne: {}\n".format(dev))

    fd = os.open(dev, os.O_RDONLY)
    stop = threading.Event()
    samples = []
    t = threading.Thread(target=read_loop, args=(fd, stop, samples))
    t.daemon = True
    t.start()

    img_dir = "/tmp/joystick-cards"
    if os.path.isdir(img_dir):
        show_image(os.path.join(img_dir, "center.png"))

    duration = 120
    print("Ne touche PAS la manette. Lecture {}s.".format(duration))
    print("Demarrage dans 3s...")
    time.sleep(3)
    print("Enregistrement en cours...")
    start = time.time()
    while time.time() - start < duration:
        remaining = int(start + duration - time.time())
        print("  reste {}s".format(remaining), end="\r", flush=True)
        time.sleep(1)
    print("  " + " " * 20, end="\r")
    stop.set()
    t.join(timeout=2)
    os.close(fd)

    print("\nAnalyse en cours...")
    stats = {}
    for ts, num, val in samples:
        if num not in stats:
            stats[num] = {"min": val, "max": val, "last": val, "count": 0, "sum": 0, "samples": []}
        s = stats[num]
        s["min"] = min(s["min"], val)
        s["max"] = max(s["max"], val)
        s["last"] = val
        s["count"] += 1
        s["sum"] += val
        s["samples"].append(val)

    print("\n=== RAPPORT 2 MINUTES ===")
    print("{:<6} {:<10} {:<10} {:<10} {:<10} {:<12} {:<10}".format(
        "Axe", "Min", "Max", "Plage", "Dernier", "Echantillons", "Drift"))
    print("-" * 70)

    drift_detected = False
    for num in sorted(stats.keys()):
        s = stats[num]
        rng = s["max"] - s["min"]
        # compute standard deviation
        mean = s["sum"] / s["count"] if s["count"] else 0
        variance = sum((v - mean) ** 2 for v in s["samples"]) / s["count"] if s["count"] else 0
        std = int(variance ** 0.5)
        # drift = last value far from 0, or range/jitter above threshold
        if abs(s["last"]) > 3000 or std > 1500 or rng > 5000:
            verdict = "OUI ({} / {})".format(s["last"], std)
            drift_detected = True
        else:
            verdict = "NON ({} / {})".format(s["last"], std)
        print("{:<6} {:<10} {:<10} {:<10} {:<10} {:<12} {:<10}".format(
            num, s["min"], s["max"], rng, s["last"], s["count"], verdict))

    print("\n=== RESUME ===")
    if drift_detected:
        print("DRIFT / GHOST INPUT DETECTE. La manette envoie des ordres sans intervention.")
    else:
        print("Aucune derive detectee. La manette reste au centre. Le probleme venait probablement d'un mouvement involontaire ou d'un reglage.")

    if os.path.isdir(img_dir):
        show_image(os.path.join(img_dir, "done.png"))


if __name__ == "__main__":
    main()