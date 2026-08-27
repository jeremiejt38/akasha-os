"""Unit tests for store_external.py -- no xbmc dependency."""

import unittest

import store_external


class TestIsValidHttpUrl(unittest.TestCase):
    def test_accepts_http_url(self):
        self.assertTrue(store_external.is_valid_http_url('http://example.com'))

    def test_accepts_https_url(self):
        self.assertTrue(store_external.is_valid_http_url('https://example.com/path?q=1'))

    def test_rejects_javascript_url(self):
        self.assertFalse(store_external.is_valid_http_url('javascript:alert(1)'))

    def test_rejects_file_url(self):
        self.assertFalse(store_external.is_valid_http_url('file:///etc/passwd'))

    def test_rejects_data_url(self):
        self.assertFalse(store_external.is_valid_http_url('data:text/html,<script>'))

    def test_rejects_relative_path(self):
        self.assertFalse(store_external.is_valid_http_url('/storage/launch.sh'))

    def test_rejects_empty_and_whitespace(self):
        self.assertFalse(store_external.is_valid_http_url(''))
        self.assertFalse(store_external.is_valid_http_url('   '))

    def test_rejects_url_without_host(self):
        self.assertFalse(store_external.is_valid_http_url('https://'))

    def test_rejects_non_string(self):
        self.assertFalse(store_external.is_valid_http_url(None))
        self.assertFalse(store_external.is_valid_http_url(123))


class TestValidateInstall(unittest.TestCase):
    def test_valid_source_url_only(self):
        ok, err = store_external.validate_install('https://example.com')
        self.assertTrue(ok)
        self.assertEqual(err, '')

    def test_valid_with_deep_link(self):
        ok, err = store_external.validate_install(
            'https://example.com', 'https://example.com/play')
        self.assertTrue(ok)
        self.assertEqual(err, '')

    def test_invalid_source_url(self):
        ok, err = store_external.validate_install('ftp://example.com')
        self.assertFalse(ok)
        self.assertIn('source_url', err)

    def test_invalid_deep_link(self):
        ok, err = store_external.validate_install(
            'https://example.com', 'javascript:alert(1)')
        self.assertFalse(ok)
        self.assertIn('deep_link', err)

    def test_none_deep_link_is_allowed(self):
        ok, err = store_external.validate_install('https://example.com', None)
        self.assertTrue(ok)

    def test_empty_deep_link_is_allowed(self):
        ok, err = store_external.validate_install('https://example.com', '')
        self.assertTrue(ok)


class TestResolveIconUrl(unittest.TestCase):
    def test_resolves_relative_store_icon(self):
        self.assertEqual(
            store_external.resolve_icon_url('video.netflix', 'icon.png'),
            store_external.STORE_RAW_BASE + '/video.netflix/icon.png')

    def test_preserves_absolute_icon_url(self):
        self.assertEqual(
            store_external.resolve_icon_url('video.netflix', 'https://cdn.example/icon.png'),
            'https://cdn.example/icon.png')

    def test_empty_icon_stays_empty(self):
        self.assertEqual(store_external.resolve_icon_url('video.netflix', ''), '')


class TestBuildSyntheticAddon(unittest.TestCase):
    def test_uses_index_entry_first(self):
        idx = {
            'name': 'YouTube',
            'version': '1.0.0',
            'description': 'Watch videos',
            'deep_link': 'https://youtube.com/tv',
            'install': {
                'type': 'external-app',
                'source_url': 'https://youtube.com',
            },
        }
        result = store_external.build_synthetic_addon('web.youtube', index_entry=idx)
        self.assertEqual(result['addonid'], 'external:web.youtube')
        self.assertEqual(result['name'], 'YouTube')
        self.assertEqual(result['version'], '1.0.0')
        self.assertEqual(result['summary'], 'Watch videos')
        self.assertEqual(result['type'], 'external-app')
        self.assertTrue(result['is_external'])
        self.assertEqual(result['store_id'], 'web.youtube')
        self.assertEqual(result['source_url'], 'https://youtube.com')
        self.assertEqual(result['deep_link'], 'https://youtube.com/tv')

    def test_falls_back_to_registry_entry(self):
        reg = {
            'name': 'Netflix',
            'version': '2.0.0',
            'install': {
                'type': 'external-app',
                'source_url': 'https://netflix.com',
            },
        }
        result = store_external.build_synthetic_addon('web.netflix', registry_entry=reg)
        self.assertEqual(result['name'], 'Netflix')
        self.assertEqual(result['version'], '2.0.0')
        self.assertEqual(result['source_url'], 'https://netflix.com')
        self.assertEqual(result['deep_link'], '')

    def test_uses_app_id_when_no_name_available(self):
        result = store_external.build_synthetic_addon('web.unknown')
        self.assertEqual(result['name'], 'web.unknown')


class TestBuildSyntheticAddons(unittest.TestCase):
    def test_skips_non_external_entries(self):
        registry = {
            'tv.francetv': {
                'addon_id': 'plugin.video.francetv',
                'version': '1.0.0',
            },
            'web.example': {
                'name': 'Example',
                'version': '1.0.0',
                'install': {
                    'type': 'external-app',
                    'source_url': 'https://example.com',
                },
            },
        }
        result = store_external.build_synthetic_addons(registry)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['store_id'], 'web.example')

    def test_returns_sorted_by_name(self):
        registry = {
            'web.beta': {
                'name': 'Beta',
                'install': {'type': 'external-app', 'source_url': 'https://beta.com'},
            },
            'web.alpha': {
                'name': 'Alpha',
                'install': {'type': 'external-app', 'source_url': 'https://alpha.com'},
            },
        }
        result = store_external.build_synthetic_addons(registry)
        self.assertEqual([a['name'] for a in result], ['Alpha', 'Beta'])

    def test_ignores_malformed_registry_values(self):
        registry = {
            'web.broken': 'not-a-dict',
            'web.ok': {
                'name': 'OK',
                'install': {'type': 'external-app', 'source_url': 'https://ok.com'},
            },
        }
        result = store_external.build_synthetic_addons(registry)
        self.assertEqual(len(result), 1)


class TestLaunchCommandArgs(unittest.TestCase):
    def test_defaults_to_source_url(self):
        args = store_external.launch_command_args(
            'https://example.com', 'Example', app_id='web.example')
        self.assertIn('https://example.com', args)
        self.assertIn('Example', args)
        self.assertIn('--unit=external-app-web.example', args)

    def test_uses_deep_link_when_present(self):
        args = store_external.launch_command_args(
            'https://example.com', 'Example',
            deep_link='https://example.com/play', app_id='web.example')
        # The deep_link should appear as the URL argument to launch.sh.
        self.assertIn('https://example.com/play', args)

    def test_sanitizes_unit_name(self):
        args = store_external.launch_command_args(
            'https://example.com', 'Example', app_id='web/app:unsafe')
        for a in args:
            if a.startswith('--unit='):
                self.assertEqual(a, '--unit=external-app-web_app_unsafe')


if __name__ == '__main__':
    unittest.main()
