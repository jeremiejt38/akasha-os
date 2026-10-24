import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import collector  # noqa: E402


class ReadMetricsTests(unittest.TestCase):
    def test_loadavg_parses(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('1.25 0.90 0.50 3/456 789\n')
            path = f.name
        try:
            self.assertEqual(collector.read_loadavg(path), (1.25, 0.90, 0.50))
        finally:
            os.unlink(path)

    def test_loadavg_missing_returns_none(self):
        self.assertIsNone(collector.read_loadavg('/nonexistent/xyz'))

    def test_mem_available_parses(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('MemTotal:       8000000 kB\nMemAvailable:    512000 kB\n')
            path = f.name
        try:
            self.assertEqual(collector.read_mem_available_mb(path), 500)
        finally:
            os.unlink(path)

    def test_temp_parses_millidegrees(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('67500\n')
            path = f.name
        try:
            self.assertEqual(collector.read_temp_c(path), 67.5)
        finally:
            os.unlink(path)


class DetectAnomaliesTests(unittest.TestCase):
    def test_clean_sample_no_events(self):
        sample = {'load1': 1.0, 'mem_avail_mb': 3000, 'temp_c': 55.0,
                  'kodi_mem_mb': 500, 'throttled': None}
        self.assertEqual(collector.detect_anomalies(sample, 10, 10.5), [])

    def test_loop_lag_detected(self):
        events = collector.detect_anomalies({}, 10, 35.0)
        self.assertEqual(events[0]['type'], 'loop_lag')

    def test_no_lag_at_boundary(self):
        self.assertEqual(collector.detect_anomalies({}, 10, 30.0), [])

    def test_each_threshold(self):
        sample = {'temp_c': 82.0, 'mem_avail_mb': 100, 'load1': 5.0,
                  'throttled': '0x50000', 'kodi_mem_mb': 50}
        types = {e['type'] for e in collector.detect_anomalies(sample, 10, 10)}
        self.assertEqual(types, {'high_temp', 'low_mem', 'high_load',
                                 'throttled', 'low_kodi_mem'})

    def test_none_values_safe(self):
        self.assertEqual(collector.detect_anomalies({}, 10, 10), [])


class ScanLogDeltaTests(unittest.TestCase):
    def _write(self, content):
        f = tempfile.NamedTemporaryFile('w', suffix='.log', delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_extracts_only_error_lines(self):
        path = self._write('INFO ok\n2026-01-01 00:00:00 ERROR bad thing\n'
                           'WARNING meh\n2026 CRITICAL: boom\n')
        try:
            _, lines = collector.scan_log_delta(path, 0)
            self.assertEqual(len(lines), 2)
            self.assertIn('ERROR bad thing', lines[0])
        finally:
            os.unlink(path)

    def test_incremental_read(self):
        path = self._write('start\n')
        try:
            off, _ = collector.scan_log_delta(path, 0)
            with open(path, 'a') as f:
                f.write('2026 ERROR late\n')
            _, lines = collector.scan_log_delta(path, off)
            self.assertEqual(lines, ['2026 ERROR late'])
        finally:
            os.unlink(path)

    def test_truncated_file_resumes_at_zero(self):
        path = self._write('x\n')
        try:
            _, lines = collector.scan_log_delta(path, 9999)
            self.assertEqual(lines, [])
        finally:
            os.unlink(path)

    def test_missing_file(self):
        off, lines = collector.scan_log_delta('/nonexistent.log', 0)
        self.assertEqual((off, lines), (0, []))


class RotatingWriterTests(unittest.TestCase):
    def test_appends_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'm.jsonl')
            w = collector.RotatingWriter(path)
            w.append({'a': 1})
            w.append({'b': 2})
            recs = [json.loads(l) for l in open(path)]
            self.assertEqual(recs, [{'a': 1}, {'b': 2}])

    def test_rotates_when_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'm.jsonl')
            w = collector.RotatingWriter(path, max_bytes=40)
            for i in range(10):
                w.append({'i': i, 'pad': 'x' * 20})
            self.assertTrue(os.path.exists(path + '.1'))
            self.assertLess(os.path.getsize(path), 200)


if __name__ == '__main__':
    unittest.main()
