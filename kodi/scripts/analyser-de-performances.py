#!/usr/bin/env python3
"""analyser-de-performances — print the Akasha OS performance report.

Reads the bounded JSONL files written by service.akasha.perfanalyzer and
prints a human-readable summary (metric window, last sample, anomaly
counts and recent events, recent kodi.log errors).

Usage on the Pi:  python3 /storage/.kodi/scripts/analyser-de-performances.py
"""
import os
import sys

sys.path.insert(0, os.path.join(
    '/storage/.kodi/addons/service.akasha.perfanalyzer', 'resources', 'lib'))

import report  # noqa: E402

if __name__ == '__main__':
    report.main()
