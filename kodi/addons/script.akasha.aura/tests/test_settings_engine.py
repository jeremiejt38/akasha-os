"""Unit tests for settings_engine.py + settings_catalog.py -- no xbmc."""

import unittest

import settings_catalog
import settings_engine


class FakeBackend(settings_engine.Backend):
    def __init__(self, settings=None, addon_store=None, run_results=None):
        self._settings = settings or []
        self.set_calls = []
        self._addons = addon_store or {}
        self._runs = run_results or {}
        self.builtins = []

    def kodi_rpc(self, method, params=None):
        if method == 'Settings.GetSettings':
            return {'settings': list(self._settings)}
        if method == 'Settings.SetSettingValue':
            self.set_calls.append((params['setting'], params['value']))
            entry = next((s for s in self._settings
                          if s['id'] == params['setting']), None)
            if entry is None:
                return False
            entry['value'] = params['value']
            return True
        return {}

    def addon_get(self, addon_id, key):
        return self._addons[(addon_id, key)]

    def addon_set(self, addon_id, key, value):
        self._addons[(addon_id, key)] = value

    def run(self, argv, timeout=5):
        for key, result in self._runs.items():
            if all(part in ' '.join(argv) for part in key.split('|')):
                return result
        return -1, ''

    def read_file(self, path):
        return self._files.get(path, '') if hasattr(self, '_files') else ''

    def exec_builtin(self, builtin):
        self.builtins.append(builtin)


SETTINGS = [
    {'id': 'videoscreen.resolution', 'type': 'enum', 'value': '1080p',
     'options': [{'value': '1080p', 'label': '1080p'},
                 {'value': '720p', 'label': '720p'}]},
    {'id': 'audiooutput.passthrough', 'type': 'boolean', 'value': False},
    {'id': 'locale.language', 'type': 'string', 'value': 'French'},
]


class TestKodiSettingsCache(unittest.TestCase):
    def test_get_and_options(self):
        cache = settings_engine.KodiSettingsCache(FakeBackend(SETTINGS))
        self.assertEqual(cache.get('videoscreen.resolution'), '1080p')
        self.assertEqual(len(cache.options('videoscreen.resolution')), 2)

    def test_unknown_id_not_in_map(self):
        cache = settings_engine.KodiSettingsCache(FakeBackend(SETTINGS))
        self.assertFalse(cache.has('nonexistent.setting'))
        self.assertIsNone(cache.get('nonexistent.setting'))

    def test_set_updates_cached_value(self):
        cache = settings_engine.KodiSettingsCache(FakeBackend(SETTINGS))
        self.assertTrue(cache.set('audiooutput.passthrough', True))
        self.assertIs(cache.get('audiooutput.passthrough'), True)

    def test_set_unknown_id_fails(self):
        backend = FakeBackend(SETTINGS)
        cache = settings_engine.KodiSettingsCache(backend)
        self.assertFalse(cache.set('nonexistent.setting', 1))


class TestSources(unittest.TestCase):
    def test_addon_source_roundtrip(self):
        backend = FakeBackend(addon_store={('a.b', 'k'): 'v'})
        src = settings_engine.AddonSettingSource('a.b', 'k')
        self.assertEqual(src.get(backend, None), 'v')
        self.assertTrue(src.set(backend, None, 'v2'))
        self.assertEqual(backend._addons[('a.b', 'k')], 'v2')

    def test_custom_source_uses_registry(self):
        backend = FakeBackend()
        settings_engine.REGISTRY['test.g'] = lambda b: 'x'
        src = settings_engine.CustomSource('test.g')
        self.assertEqual(src.get(backend, None), 'x')
        self.assertTrue(src.available(backend, None))

    def test_connman_wifi_toggle(self):
        calls = []

        class B(FakeBackend):
            def run(self, argv, timeout=5):
                calls.append(argv)
                return (0, '/net/connman/technology/wifi\n'
                           '  Powered = True\n') \
                    if 'technologies' in argv else (0, '')

        backend = B()
        self.assertTrue(settings_engine._system_get(
            backend, 'connman', 'wifi_enabled'))
        self.assertTrue(settings_engine._system_set(
            backend, 'connman', 'wifi_enabled', False))
        self.assertEqual(calls[-1][:2], ['connmanctl', 'disable'])

    def test_net_status_parses_wifi(self):
        backend = FakeBackend(run_results={
            'connmanctl services': (0, '*AR Maison wifi_abc_managed_psk\n')})
        status = settings_engine._system_get(
            backend, 'connman', 'net_status')
        self.assertEqual(status['kind'], 'wifi')
        self.assertEqual(status['name'], 'Maison')

    def test_bluetooth_devices_parsed(self):
        backend = FakeBackend(run_results={
            'bluetoothctl devices Paired':
                (0, 'Device AA:BB:CC:DD:EE:FF Xbox Controller\n'
                    'Device 11:22:33:44:55:66 Fire TV Remote\n')})
        devices = settings_engine._system_get(
            backend, 'bluetooth', 'paired_devices')
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]['name'], 'Xbox Controller')
        self.assertEqual(devices[1]['mac'], '11:22:33:44:55:66')


class TestCatalog(unittest.TestCase):
    def test_unique_item_ids(self):
        ids = []
        for cat in settings_catalog.build_categories():
            for item in cat['items']:
                ids.append(item['id'])
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_label_is_a_known_i18n_key(self):
        import i18n
        for cat in settings_catalog.build_categories():
            self.assertIn(cat['title'], i18n.STRINGS)
            for item in cat['items']:
                self.assertIn(item['label'], i18n.STRINGS,
                              item['id'])
                if item.get('help'):
                    self.assertIn(item['help'], i18n.STRINGS, item['id'])

    def test_source_shapes(self):
        valid = {'kodi': 2, 'addon': 3, 'system': 2, 'custom': 2,
                 'action': 2, 'window': 2, 'script': 2, 'addonui': 2}
        for cat in settings_catalog.build_categories():
            for item in cat['items']:
                src = item.get('source')
                self.assertIsNotNone(src, item['id'])
                self.assertIn(src[0], valid, item['id'])
                self.assertEqual(len(src), valid[src[0]], item['id'])

    def test_catalog_kodi_ids_listed(self):
        ids = settings_catalog.kodi_setting_ids()
        self.assertIn('videoscreen.resolution', ids)
        self.assertIn('locale.language', ids)


if __name__ == '__main__':
    unittest.main()
