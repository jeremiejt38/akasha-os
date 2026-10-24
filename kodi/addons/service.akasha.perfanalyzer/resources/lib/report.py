"""Akasha performance analyzer — report generation.

Pure logic (stdlib only): reads the JSONL files written by the collector
and produces a compact human-readable summary for the
`analyser-de-performances` CLI.
"""
import json
import os
import time


def _iter_records(paths):
    """Yield parsed JSON records from a list of JSONL files (oldest first:
    rotated .1 before the live file)."""
    for path in paths:
        try:
            with open(path, 'r', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue
        except OSError:
            continue


def load_metrics(base_path):
    """All metric records, rotated file first then the live one."""
    return list(_iter_records(['{}.1'.format(base_path), base_path]))


def load_errors(base_path):
    return list(_iter_records(['{}.1'.format(base_path), base_path]))


def summarize(metrics, errors, now=None, max_events=20):
    """Build the report dict from collected records.

    metrics: list of {'ts': epoch, sample fields, 'events': [...]}
    errors:  list of {'ts': epoch, 'lines': [...]}
    Returns a dict consumed by `format_report`.
    """
    now = now or time.time()
    anomaly_counts = {}
    anomaly_last = []
    samples = 0
    for rec in metrics:
        if rec.get('type') == 'boot':
            # Boot marker written by autostart.sh before Kodi starts.
            anomaly_last.append((rec.get('ts'), 'boot', 'démarrage système'))
            continue
        samples += 1
        for ev in rec.get('events') or []:
            t = ev.get('type', 'unknown')
            anomaly_counts[t] = anomaly_counts.get(t, 0) + 1
            anomaly_last.append((rec.get('ts'), t, ev.get('detail', '')))
    err_lines = sum(len(e.get('lines') or []) for e in errors)

    ts_values = [r.get('ts') for r in metrics if r.get('ts')]
    summary = {
        'generated_at': now,
        'window': {
            'first': min(ts_values) if ts_values else None,
            'last': max(ts_values) if ts_values else None,
            'samples': samples,
        },
        'anomaly_counts': anomaly_counts,
        'anomaly_total': sum(anomaly_counts.values()),
        'recent_events': anomaly_last[-max_events:],
        'error_lines': err_lines,
        'recent_errors': [
            (e.get('ts'), l) for e in errors for l in (e.get('lines') or [])
        ][-10:],
        'last_sample': next(
            (r for r in reversed(metrics) if r.get('type') != 'boot'), None),
    }
    return summary


def _fmt_ts(ts):
    if ts is None:
        return '-'
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))


def format_report(summary):
    """Render `summarize()` output as plain text (French, user-facing)."""
    lines = ['=== Analyseur de performances Akasha OS ===']
    w = summary['window']
    lines.append('Fenetre  : {} -> {} ({} echantillons)'.format(
        _fmt_ts(w['first']), _fmt_ts(w['last']), w['samples']))
    last = summary.get('last_sample') or {}
    lines.append('Instant  : load1={} mem={}MB temp={}C kodi_mem={}MB playing={}'.format(
        last.get('load1', '?'), last.get('mem_avail_mb', '?'),
        last.get('temp_c', '?'), last.get('kodi_mem_mb', '?'),
        last.get('playing', '?')))
    lines.append('Anomalies: {} au total'.format(summary['anomaly_total']))
    for t, n in sorted(summary['anomaly_counts'].items()):
        lines.append('  - {}: {}'.format(t, n))
    if summary['recent_events']:
        lines.append('Derniers evenements :')
        for ts, t, detail in summary['recent_events'][-8:]:
            lines.append('  {} [{}] {}'.format(_fmt_ts(ts), t, detail))
    lines.append('Erreurs kodi.log : {} lignes'.format(summary['error_lines']))
    for ts, l in summary['recent_errors'][-8:]:
        lines.append('  {} {}'.format(_fmt_ts(ts), l[:160]))
    return '\n'.join(lines)


def metrics_path():
    return '/storage/.config/akasha-os/perf/metrics.jsonl'


def errors_path():
    return '/storage/.config/akasha-os/perf/errors.jsonl'


def main():
    summary = summarize(load_metrics(metrics_path()), load_errors(errors_path()))
    print(format_report(summary))


if __name__ == '__main__':
    main()
