import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import report  # noqa: E402


class SummarizeTests(unittest.TestCase):
    def test_empty_inputs(self):
        s = report.summarize([], [], now=1000)
        self.assertEqual(s['anomaly_total'], 0)
        self.assertEqual(s['window']['samples'], 0)
        self.assertIn('0 au total', report.format_report(s))

    def test_boot_marker_becomes_event_not_sample(self):
        metrics = [
            {'ts': 100, 'type': 'boot'},
            {'ts': 110, 'load1': 1.0},
        ]
        s = report.summarize(metrics, [])
        self.assertEqual(s['window']['samples'], 1)
        self.assertEqual(s['recent_events'][-1][1], 'boot')

    def test_counts_anomalies_and_errors(self):
        metrics = [
            {'ts': 100, 'events': [{'type': 'high_temp', 'detail': '82C'}]},
            {'ts': 110, 'events': [{'type': 'high_temp', 'detail': '85C'},
                                   {'type': 'loop_lag', 'detail': '40s'}]},
            {'ts': 120},
        ]
        errors = [{'ts': 105, 'lines': ['ERROR a', 'ERROR b']}]
        s = report.summarize(metrics, errors, now=200)
        self.assertEqual(s['anomaly_counts']['high_temp'], 2)
        self.assertEqual(s['anomaly_total'], 3)
        self.assertEqual(s['error_lines'], 2)
        self.assertEqual(s['window']['first'], 100)
        self.assertEqual(s['last_sample']['ts'], 120)

    def test_recent_events_capped(self):
        metrics = [{'ts': i, 'events': [{'type': 'x', 'detail': str(i)}]}
                   for i in range(50)]
        s = report.summarize(metrics, [], max_events=10)
        self.assertEqual(len(s['recent_events']), 10)

    def test_format_report_renders(self):
        s = report.summarize(
            [{'ts': 1700000000, 'load1': 1.2, 'mem_avail_mb': 2000,
              'temp_c': 55.0, 'kodi_mem_mb': 300, 'playing': True,
              'events': [{'type': 'high_load', 'detail': 'load1 5.0'}]}],
            [{'ts': 1700000001, 'lines': ['ERROR x']}],
            now=1700000100)
        text = report.format_report(s)
        self.assertIn('high_load', text)
        self.assertIn('ERROR x', text)
        self.assertIn('echantillons', text)


if __name__ == '__main__':
    unittest.main()
