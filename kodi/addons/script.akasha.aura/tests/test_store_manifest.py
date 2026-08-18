"""Unit tests for store_manifest.py — no xbmc dependency."""

import json
import os
import tempfile
import unittest

import store_manifest


class TestLoadManifest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, 'resources', 'data')
        os.makedirs(self.data_dir)
        self.manifest_file = os.path.join(self.data_dir, 'store_manifest.json')

    def _write_manifest(self, content):
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_load_manifest_returns_entries(self):
        self._write_manifest(json.dumps({
            'version': 1,
            'entries': [
                {'addonid': 'plugin.video.francetv', 'name': 'france.tv', 'summary': 'Replay'},
                {'addonid': 'plugin.video.vimeo', 'name': 'Vimeo', 'summary': 'Videos'},
            ],
        }))
        entries = store_manifest.load_manifest(self.tmpdir)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['addonid'], 'plugin.video.francetv')
        self.assertEqual(entries[0]['name'], 'france.tv')

    def test_entries_missing_addonid_are_skipped(self):
        self._write_manifest(json.dumps({
            'entries': [
                {'name': 'No id', 'summary': 'x'},
                {'addonid': 'plugin.video.vimeo', 'name': 'Vimeo'},
            ],
        }))
        entries = store_manifest.load_manifest(self.tmpdir)
        self.assertEqual([e['addonid'] for e in entries], ['plugin.video.vimeo'])

    def test_missing_file_returns_empty(self):
        self.assertEqual(store_manifest.load_manifest('/nonexistent'), [])

    def test_malformed_json_returns_empty(self):
        self._write_manifest('not json')
        self.assertEqual(store_manifest.load_manifest(self.tmpdir), [])


class TestWithInstallStatus(unittest.TestCase):
    def test_marks_installed_entries(self):
        entries = [
            {'addonid': 'plugin.video.francetv', 'name': 'france.tv', 'summary': ''},
            {'addonid': 'plugin.video.vimeo', 'name': 'Vimeo', 'summary': ''},
        ]
        result = store_manifest.with_install_status(entries, ['plugin.video.vimeo'])
        by_id = {e['addonid']: e for e in result}
        self.assertFalse(by_id['plugin.video.francetv']['installed'])
        self.assertTrue(by_id['plugin.video.vimeo']['installed'])


if __name__ == '__main__':
    unittest.main()
