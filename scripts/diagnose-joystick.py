#!/usr/bin/env python3
"""Diagnostic rapide des joysticks Xbox Wireless sur LibreELEC/Linux.

Le script guide l'utilisateur pendant ~50s, enregistre les valeurs des axes
joystick et affiche un rapport final par stick (gauche / droit) avec :
- plages min/max,
- retour au centre,
- axes bloqués,
- bruit / jitter.

Nécessite que Kodi soit arrêté car peripheral.joystick garde le device.
"""
import os
import struct
import fcntl
import time
import threading
import select
import sys

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

JSIOCGAXES = 0x80016a11
JSIOCGBUTTONS = 0x80016a12

def JSIOCGNAME(l):
    return (2 << 30) | (l << 16) | (0x6a << 8) | 0x13


def find_joystick():
    """Trouve un joystick Xbox-compatible parmi /dev/input/js*."""
    devices = []
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
                devices.append((dev, name, axes, btns))
        except Exception as e:
            print("  Erreur probe {}: {}".format(dev, e), file=sys.stderr)

    for dev, name, axes, btns in devices:
        if axes >= 4 and ("Wireless" in name or "Bluetooth" in name.lower()):
            return dev, name, axes, btns
    for dev, name, axes, btns in devices:
        if axes >= 4 and ("Microsoft" in name or "X-Box" in name or "Xbox" in name or "360" in name):
            return dev, name, axes, btns

    best = max(devices, key=lambda x: x[2]) if devices else None
    if best and best[2] >= 2:
        return best
    return None, None, 0, 0


def read_joystick(fd, stop, samples, axis_state):
    """Boucle de lecture des axes joystick en arrière-plan."""
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
        event_type = typ & 0x7f
        if event_type == JS_EVENT_AXIS:
            now = time.time()
            samples.append((now, number, value))
            axis_state[number] = value


def phase(name, duration, message, state):
    state["current"] = name
    state["deadline"] = time.time() + duration
    print("\n[{}] {}".format(state["phase_idx"], message))
    state["phase_idx"] += 1
    while time.time() < state["deadline"]:
        remaining = int(state["deadline"] - time.time())
        if remaining != state["last_remaining"]:
            print("  reste {}s...".format(remaining), end="\r", flush=True)
            state["last_remaining"] = remaining
        time.sleep(0.1)
    print("  " + " " * 20, end="\r")
    state["last_remaining"] = -1


def get_phase_samples(samples, start, end):
    return [s for s in samples if start <= s[0] <= end]


def active_axes(phase_samples, threshold=500):
    """Return axes that moved at least `threshold` during the phase."""
    data = {}
    for ts, num, val in phase_samples:
        if num not in data:
            data[num] = []
        data[num].append(val)
    result = {}
    for num, vals in data.items():
        rng = max(vals) - min(vals)
        if rng >= threshold:
            result[num] = {
                "min": min(vals),
                "max": max(vals),
                "range": rng,
                "last": vals[-1],
                "count": len(vals),
                "variance": sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals),
            }
    return result


def detect_stick(active, possible_x, possible_y):
    """Pick the two most active axes from possible lists as X and Y."""
    axes = sorted(active.items(), key=lambda x: x[1]["range"], reverse=True)
    x = y = None
    for num, info in axes:
        if x is None and num in possible_x:
            x = (num, info)
        elif y is None and num in possible_y:
            y = (num, info)
        if x and y:
            break
    return x, y


def print_report_per_phase(phases, samples, naxes):
    print("\n=== RAPPORT DETAILLE PAR PHASE ===")
    for pname, start, end, desc in phases:
        psamples = get_phase_samples(samples, start, end)
        act = active_axes(psamples)
        print("\n[{}] {}".format(pname, desc))
        if not act:
            print("  Aucun axe actif")
            continue
        for num in sorted(act.keys()):
            d = act[num]
            print("  Axe {}: min={:<7} max={:<7} plage={:<7} dernier={:<7} echantillons={}".format(
                num, d["min"], d["max"], d["range"], d["last"], d["count"]
            ))


def print_stick_report(label, x, y, full_range=60000):
    if not x or not y:
        print("  {}: impossible d'identifier les axes".format(label))
        return

    xnum, xi = x
    ynum, yi = y
    issues = []

    x_range_ok = xi["range"] >= full_range * 0.85
    y_range_ok = yi["range"] >= full_range * 0.85
    x_center = abs(xi["last"]) < 3000
    y_center = abs(yi["last"]) < 3000

    if not x_range_ok:
        issues.append("axe X a plage reduite ({})".format(xi["range"]))
    if not y_range_ok:
        issues.append("axe Y a plage reduite ({})".format(yi["range"]))
    if not x_center:
        issues.append("axe X ne revient pas au centre (dernier={})".format(xi["last"]))
    if not y_center:
        issues.append("axe Y ne revient pas au centre (dernier={})".format(yi["last"]))
    if xi["count"] < 5 or yi["count"] < 5:
        issues.append("trop peu d'evenements")

    if issues:
        print("  {}: PROBLEME - {}".format(label, "; ".join(issues)))
    else:
        print("  {}: OK (plage X={}, Y={}, retour centre OK)".format(
            label, xi["range"], yi["range"]
        ))


def main():
    print("=== Diagnostic Joystick Xbox Wireless ===\n")
    print("Recherche du joystick...")
    dev, name, naxes, nbtns = find_joystick()
    if not dev:
        print("Aucun joystick trouve.")
        sys.exit(1)
    print("\nSelectionne: {} ({} axes, {} boutons)\n".format(dev, naxes, nbtns))

    fd = os.open(dev, os.O_RDONLY)
    try:
        stop = threading.Event()
        samples = []
        axis_state = {}
        thread = threading.Thread(target=read_joystick, args=(fd, stop, samples, axis_state))
        thread.daemon = True
        thread.start()

        state = {"phase_idx": 1, "last_remaining": -1, "current": None}
        phases = []

        print("Prepare la manette. Lecture demarre dans 2s...")
        time.sleep(2)

        # Phase 1: centre (baseline)
        t0 = time.time()
        phase("centre", 3, "Ne touche a rien - position centree", state)
        phases.append(("centre", t0, time.time(), "position centree"))

        # Phase 2: left stick circles
        t0 = time.time()
        phase("lg_cercles", 10, "JOY GAUCHE : faire 2 ou 3 cercles complets (lentement)", state)
        phases.append(("lg_cercles", t0, time.time(), "joy gauche cercles"))

        # Phase 3: left stick release
        t0 = time.time()
        phase("lg_relache", 3, "JOY GAUCHE : relacher completement", state)
        phases.append(("lg_relache", t0, time.time(), "joy gauche relache"))

        # Phase 4: left stick up/down
        t0 = time.time()
        phase("lg_haut_bas", 5, "JOY GAUCHE : tout en HAUT puis tout en BAS (2x)", state)
        phases.append(("lg_haut_bas", t0, time.time(), "joy gauche haut/bas"))

        # Phase 5: right stick circles
        t0 = time.time()
        phase("ld_cercles", 10, "JOY DROIT : faire 2 ou 3 cercles complets (lentement)", state)
        phases.append(("ld_cercles", t0, time.time(), "joy droit cercles"))

        # Phase 6: right stick release
        t0 = time.time()
        phase("ld_relache", 3, "JOY DROIT : relacher completement", state)
        phases.append(("ld_relache", t0, time.time(), "joy droit relache"))

        # Phase 7: right stick up/down
        t0 = time.time()
        phase("ld_haut_bas", 5, "JOY DROIT : tout en HAUT puis tout en BAS (2x)", state)
        phases.append(("ld_haut_bas", t0, time.time(), "joy droit haut/bas"))

        # Phase 8: final center
        t0 = time.time()
        phase("fin", 3, "Relache tout - position centree", state)
        phases.append(("fin", t0, time.time(), "position centree"))

        stop.set()
        thread.join(timeout=2)
    finally:
        os.close(fd)

    print("\nDiagnostic termine. Analyse en cours...")
    print_report_per_phase(phases, samples, naxes)

    # Identify left/right stick axes by activity during their dedicated phases
    lg_cercles = active_axes(get_phase_samples(samples, phases[1][1], phases[1][2]))
    ld_cercles = active_axes(get_phase_samples(samples, phases[4][1], phases[4][2]))

    # Try common mappings: left X/Y are 0/1 or 0/1/2; right X/Y are 2/3 or 3/4
    left_x, left_y = detect_stick(lg_cercles, [0, 1, 2, 3], [0, 1, 2, 3])
    right_x, right_y = detect_stick(ld_cercles, [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 5])

    print("\n=== ANALYSE JOYSTICKS ===")
    print("Axes choisis par calibration (phase cercles) :")
    if left_x and left_y:
        print("  Gauche -> X=axe {}  Y=axe {}".format(left_x[0], left_y[0]))
    if right_x and right_y:
        print("  Droit  -> X=axe {}  Y=axe {}".format(right_x[0], right_y[0]))
    print()
    print_stick_report("Joy Gauche", left_x, left_y)
    print_stick_report("Joy Droit", right_x, right_y)


if __name__ == "__main__":
    main()