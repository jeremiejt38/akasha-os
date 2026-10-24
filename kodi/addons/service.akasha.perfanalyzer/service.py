"""Akasha performance analyzer — lightweight background collector.

Runs as a Kodi service from startup (the earliest point an addon can
start). Every SAMPLE_INTERVAL seconds it records one JSON line of system +
Kodi metrics, scans kodi.log for new ERROR/CRITICAL lines, and flags
anomalies (system stalls via tick lag, high temperature, throttling,
memory pressure, high load). Records land in bounded rotating JSONL
files under /storage/.config/akasha-os/perf/ and are summarised later by
the `analyser-de-performances` command — nothing is kept in memory.

Deliberately cheap: two file reads and one Kodi call per tick, plus one
vcgencmd subprocess every THROTTLE_EVERY ticks.
"""
import os
import subprocess
import sys
import time

import xbmc

ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))
import collector  # noqa: E402
import report  # noqa: E402

SAMPLE_INTERVAL = 10.0
THROTTLE_EVERY = 6                 # vcgencmd check every ~60s
KODI_LOG = '/storage/.kodi/temp/kodi.log'
PERF_DIR = '/storage/.config/akasha-os/perf'

_metrics_writer = collector.RotatingWriter(report.metrics_path())
_errors_writer = collector.RotatingWriter(report.errors_path())


def _log(msg):
    xbmc.log('Akasha PerfAnalyzer: {}'.format(msg), xbmc.LOGINFO)


def _kodi_free_mem_mb():
    try:
        return xbmc.getFreeMem()
    except Exception:
        return None


def _throttled_state():
    """vcgencmd hex status, or None if unavailable (non-Pi host)."""
    try:
        out = subprocess.check_output(
            ['vcgencmd', 'get_throttled'], timeout=2).decode()
        val = out.strip().split('=')[-1]
        return val if val != '0x0' else None
    except Exception:
        return None


def _collect_sample():
    load = collector.read_loadavg()
    return {
        'load1': load[0] if load else None,
        'load5': load[1] if load else None,
        'load15': load[2] if load else None,
        'mem_avail_mb': collector.read_mem_available_mb(),
        'temp_c': collector.read_temp_c(),
        'kodi_mem_mb': _kodi_free_mem_mb(),
        'playing': bool(xbmc.Player().isPlaying()),
        'idle_s': int(xbmc.getGlobalIdleTime()),
    }


def main():
    _log('starting (interval {}s)'.format(int(SAMPLE_INTERVAL)))
    os.makedirs(PERF_DIR, exist_ok=True)
    monitor = xbmc.Monitor()
    log_offset = 0
    tick = 0
    last_tick = time.time()

    while not monitor.abortRequested():
        now = time.time()
        actual_interval = now - last_tick
        last_tick = now
        tick += 1

        sample = _collect_sample()
        if tick % THROTTLE_EVERY == 0:
            sample['throttled'] = _throttled_state()

        events = collector.detect_anomalies(
            sample, SAMPLE_INTERVAL, actual_interval)
        record = {'ts': int(now)}
        record.update(sample)
        if events:
            record['events'] = events
            for ev in events:
                xbmc.log('Akasha PerfAnalyzer: {} — {}'.format(
                    ev['type'], ev['detail']), xbmc.LOGWARNING)
        _metrics_writer.append(record)

        log_offset, err_lines = collector.scan_log_delta(KODI_LOG, log_offset)
        if err_lines:
            _errors_writer.append({'ts': int(now), 'lines': err_lines})

        monitor.waitForAbort(SAMPLE_INTERVAL)

    _log('stopping')


if __name__ == '__main__':
    main()
