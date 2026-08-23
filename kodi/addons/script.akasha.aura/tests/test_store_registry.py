"""Unit tests for store_registry.py -- no xbmc dependency."""

import os
import tempfile
import unittest

import store_registry


class TestLoadRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, 'nested', 'registry.json')

    def test_missing_file_returns_empty(self):
        self.assertEqual(store_registry.load_registry(self.path), {})

    def test_malformed_json_returns_empty(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'w') as f:
            f.write('not json')
        self.assertEqual(store_registry.load_registry(self.path), {})

    def test_non_dict_entries_returns_empty(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'w') as f:
            f.write('{"entries": ["not", "a", "dict"]}')
        self.assertEqual(store_registry.load_registry(self.path), {})


class TestRecordInstallUninstall(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, 'registry.json')

    def test_record_install_then_load(self):
        store_registry.record_install('tv.francetv', '1.4.2', '2026-08-23T00:00:00', path=self.path)
        entries = store_registry.load_registry(self.path)
        self.assertEqual(entries['tv.francetv']['version'], '1.4.2')
        self.assertEqual(entries['tv.francetv']['installed_at'], '2026-08-23T00:00:00')

    def test_record_uninstall_removes_entry(self):
        store_registry.record_install('tv.francetv', '1.4.2', '2026-08-23T00:00:00', path=self.path)
        store_registry.record_uninstall('tv.francetv', self.path)
        self.assertEqual(store_registry.load_registry(self.path), {})

    def test_uninstall_unknown_app_is_a_noop(self):
        store_registry.record_uninstall('never.installed', self.path)
        self.assertEqual(store_registry.load_registry(self.path), {})

    def test_multiple_apps_coexist(self):
        store_registry.record_install('a.b', '1.0.0', 't1', path=self.path)
        store_registry.record_install('c.d', '2.0.0', 't2', path=self.path)
        entries = store_registry.load_registry(self.path)
        self.assertEqual(set(entries), {'a.b', 'c.d'})

    def test_reinstall_updates_version(self):
        store_registry.record_install('a.b', '1.0.0', 't1', path=self.path)
        store_registry.record_install('a.b', '1.1.0', 't2', path=self.path)
        entries = store_registry.load_registry(self.path)
        self.assertEqual(entries['a.b']['version'], '1.1.0')
        self.assertEqual(entries['a.b']['installed_at'], 't2')

    def test_records_addon_id_when_given(self):
        store_registry.record_install(
            'tv.francetv', '1.4.2', 't1', addon_id='plugin.video.francetv', path=self.path)
        entries = store_registry.load_registry(self.path)
        self.assertEqual(entries['tv.francetv']['addon_id'], 'plugin.video.francetv')

    def test_addon_id_defaults_to_none(self):
        store_registry.record_install('video.netflix', '1.0.0', 't1', path=self.path)
        entries = store_registry.load_registry(self.path)
        self.assertIsNone(entries['video.netflix']['addon_id'])


class TestAddonIdToStoreId(unittest.TestCase):
    def test_maps_addon_id_to_store_id(self):
        registry = {
            'tv.francetv': {'addon_id': 'plugin.video.francetv'},
            'video.netflix': {'addon_id': None},
        }
        result = store_registry.addon_id_to_store_id(registry)
        self.assertEqual(result, {'plugin.video.francetv': 'tv.francetv'})

    def test_empty_registry_returns_empty_map(self):
        self.assertEqual(store_registry.addon_id_to_store_id({}), {})


class TestVisibleAppIds(unittest.TestCase):
    def test_returns_intersection(self):
        registry = {'a.b': {}, 'c.d': {}}
        index = {'a.b': {}, 'e.f': {}}
        visible, orphaned = store_registry.visible_app_ids(registry, index)
        self.assertEqual(visible, {'a.b'})

    def test_reports_orphaned_ids(self):
        registry = {'a.b': {}, 'c.d': {}}
        index = {'a.b': {}}
        visible, orphaned = store_registry.visible_app_ids(registry, index)
        self.assertEqual(orphaned, {'c.d'})

    def test_empty_registry_is_never_visible(self):
        visible, orphaned = store_registry.visible_app_ids({}, {'a.b': {}})
        self.assertEqual(visible, set())
        self.assertEqual(orphaned, set())


if __name__ == '__main__':
    unittest.main()
