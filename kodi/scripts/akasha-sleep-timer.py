#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time

STATE_FILE = '/storage/.config/akasha-os/sleep-timer.json'
SLEEP_SCRIPT = '/storage/.kodi/scripts/akasha-sleep.py'


def read_state(path=STATE_FILE):
    try:
        with open(path) as f:
            state = json.load(f)
        return state if float(state['target']) > time.time() else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_state(target, pid=None, path=STATE_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump({'target': float(target), 'pid': int(pid or os.getpid())}, f)
    os.replace(tmp, path)


def remove_state(path=STATE_FILE):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def run(target):
    write_state(target)
    while time.time() < target:
        state = read_state()
        if not state or state.get('pid') != os.getpid() or state.get('target') != target:
            return
        time.sleep(min(1, max(0, target - time.time())))
    remove_state()
    subprocess.Popen([sys.executable, SLEEP_SCRIPT, '--force-cec'], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    run(float(sys.argv[1]))
