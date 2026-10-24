"""Akasha performance analyzer — pure collection and anomaly logic.

Stdlib-only (no `xbmc*`) so every piece is unit-testable on any host.
The Kodi-facing loop lives in `service.py`; this module knows how to read
system metrics from /proc and /sys, detect abnormal conditions, scan the
Kodi log incrementally for errors, and append bounded JSONL records.
"""
import json
import os

PROC_LOADAVG = '/proc/loadavg'
PROC_MEMINFO = '/proc/meminfo'
SYS_TEMP = '/sys/class/thermal/thermal_zone0/temp'

# Anomaly thresholds (all overridable for tests).
LOOP_LAG_FACTOR = 3.0          # tick took > factor * interval -> system stall
HIGH_TEMP_C = 80.0
LOW_MEM_AVAIL_MB = 150
HIGH_LOAD1 = 4.0
LOW_KODI_MEM_MB = 100
MAX_ERRORS_PER_TICK = 50       # cap so a log spam burst stays bounded
LOG_MAX_BYTES = 512 * 1024     # rotate metrics file at 512 KB
LOG_BACKUPS = 1                # keep one .1 rotated copy
ERROR_MARKERS = (' ERROR ', 'CRITICAL:', 'ERROR:')


def read_loadavg(path=PROC_LOADAVG):
    """Return (load1, load5, load15) floats, or None on failure."""
    try:
        with open(path) as f:
            parts = f.read().split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (OSError, ValueError, IndexError):
        return None


def read_mem_available_mb(path=PROC_MEMINFO):
    """Return MemAvailable in MB, or None on failure."""
    try:
        with open(path) as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def read_temp_c(path=SYS_TEMP):
    """Return CPU temperature in Celsius, or None on failure."""
    try:
        with open(path) as f:
            return int(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def detect_anomalies(sample, expected_interval_s, actual_interval_s,
                     thresholds=None):
    """Return a list of anomaly event dicts for one sample.

    `sample` keys (all optional): load1, mem_avail_mb, temp_c, throttled,
    kodi_mem_mb. Each event is {type, detail} — detail is a short string
    safe for a JSONL log line.
    """
    t = thresholds or {}
    lag_factor = t.get('loop_lag_factor', LOOP_LAG_FACTOR)
    high_temp = t.get('high_temp_c', HIGH_TEMP_C)
    low_mem = t.get('low_mem_avail_mb', LOW_MEM_AVAIL_MB)
    high_load = t.get('high_load1', HIGH_LOAD1)
    low_kodi_mem = t.get('low_kodi_mem_mb', LOW_KODI_MEM_MB)

    events = []
    if (expected_interval_s > 0 and actual_interval_s is not None
            and actual_interval_s > expected_interval_s * lag_factor):
        events.append({
            'type': 'loop_lag',
            'detail': 'tick expected {:.0f}s took {:.1f}s'.format(
                expected_interval_s, actual_interval_s),
        })
    if sample.get('temp_c') is not None and sample['temp_c'] >= high_temp:
        events.append({
            'type': 'high_temp',
            'detail': '{:.1f}C'.format(sample['temp_c']),
        })
    if sample.get('mem_avail_mb') is not None and sample['mem_avail_mb'] <= low_mem:
        events.append({
            'type': 'low_mem',
            'detail': '{}MB available'.format(sample['mem_avail_mb']),
        })
    if sample.get('load1') is not None and sample['load1'] >= high_load:
        events.append({
            'type': 'high_load',
            'detail': 'load1 {:.2f}'.format(sample['load1']),
        })
    if sample.get('throttled'):
        events.append({
            'type': 'throttled',
            'detail': str(sample['throttled']),
        })
    if sample.get('kodi_mem_mb') is not None and sample['kodi_mem_mb'] <= low_kodi_mem:
        events.append({
            'type': 'low_kodi_mem',
            'detail': '{}MB free in Kodi'.format(sample['kodi_mem_mb']),
        })
    return events


def scan_log_delta(path, offset, max_lines=MAX_ERRORS_PER_TICK,
                   markers=ERROR_MARKERS):
    """Read new bytes of `path` since `offset` and extract error lines.

    Returns (new_offset, error_lines). Handles rotation/truncation by
    resuming at 0 when the file shrank. Tolerates a missing file.
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return offset, []
    if offset > size:
        offset = 0
    try:
        with open(path, 'r', errors='replace') as f:
            f.seek(offset)
            data = f.read()
            new_offset = f.tell()
    except OSError:
        return offset, []
    errors = [line for line in data.splitlines()
              if any(m in line for m in markers)]
    return new_offset, errors[:max_lines]


class RotatingWriter:
    """Append JSON lines to a file, rotating at `max_bytes` keeping `backups`.

    Files: `path` plus `path.1` … `path.<backups>` (oldest dropped).
    """

    def __init__(self, path, max_bytes=LOG_MAX_BYTES, backups=LOG_BACKUPS):
        self.path = path
        self.max_bytes = max_bytes
        self.backups = backups

    def append(self, record):
        line = json.dumps(record, separators=(',', ':'), sort_keys=True)
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if (os.path.exists(self.path)
                    and os.path.getsize(self.path) + len(line) + 1 > self.max_bytes):
                self._rotate()
            with open(self.path, 'a') as f:
                f.write(line + '\n')
        except OSError:
            pass

    def _rotate(self):
        for i in range(self.backups, 0, -1):
            src = self.path if i == 1 else '{}.{}'.format(self.path, i - 1)
            dst = '{}.{}'.format(self.path, i)
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                if os.path.exists(src):
                    os.rename(src, dst)
            except OSError:
                pass
