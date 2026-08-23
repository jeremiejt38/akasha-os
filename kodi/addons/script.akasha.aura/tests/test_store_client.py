"""Unit tests for store_client.py -- no xbmc/network dependency."""

import os
import tempfile
import unittest

import store_client


SAMPLE_RAW_INDEX = {
    'store_version': 1,
    'generated_at': '2026-08-19T00:00:00+00:00',
    'entries': [
        {'id': 'tv.francetv', 'name': 'france.tv', 'category': 'replay',
         'description': 'Replay France Televisions.'},
        {'id': 'video.netflix', 'name': 'Netflix', 'category': 'svod',
         'description': 'Films et series.'},
    ],
}


class TestNormalizeIndex(unittest.TestCase):
    def test_normalizes_valid_payload(self):
        result = store_client._normalize_index(SAMPLE_RAW_INDEX)
        self.assertEqual(result['generated_at'], '2026-08-19T00:00:00+00:00')
        self.assertEqual(len(result['entries']), 2)

    def test_non_dict_payload_returns_empty(self):
        result = store_client._normalize_index(['not', 'a', 'dict'])
        self.assertEqual(result['entries'], [])

    def test_entries_without_id_are_skipped(self):
        result = store_client._normalize_index({
            'entries': [{'name': 'No id'}, {'id': 'a.b', 'name': 'Has id'}],
        })
        self.assertEqual([e['id'] for e in result['entries']], ['a.b'])

    def test_missing_entries_key_returns_empty_list(self):
        result = store_client._normalize_index({'generated_at': 'x'})
        self.assertEqual(result['entries'], [])


class TestFetchIndex(unittest.TestCase):
    def test_fetch_success_returns_normalized_with_timestamp(self):
        result = store_client.fetch_index(lambda url: SAMPLE_RAW_INDEX)
        self.assertEqual(len(result['entries']), 2)
        self.assertIsNotNone(result['fetched_at'])

    def test_fetch_failure_returns_none(self):
        def _boom(url):
            raise OSError('network down')
        self.assertIsNone(store_client.fetch_index(_boom))


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.tmpdir, 'nested', 'cache.json')

    def test_save_and_load_roundtrip(self):
        data = {'generated_at': 'x', 'entries': [], 'fetched_at': 123.0}
        self.assertTrue(store_client.save_cache(self.cache_path, data))
        self.assertEqual(store_client.load_cache(self.cache_path), data)

    def test_load_missing_file_returns_none(self):
        self.assertIsNone(store_client.load_cache(self.cache_path))

    def test_load_malformed_file_returns_none(self):
        os.makedirs(os.path.dirname(self.cache_path))
        with open(self.cache_path, 'w') as f:
            f.write('not json')
        self.assertIsNone(store_client.load_cache(self.cache_path))


class TestIsCacheFresh(unittest.TestCase):
    def test_none_cache_is_not_fresh(self):
        self.assertFalse(store_client.is_cache_fresh(None, 100))

    def test_cache_without_fetched_at_is_not_fresh(self):
        self.assertFalse(store_client.is_cache_fresh({'entries': []}, 100))

    def test_fresh_within_max_age(self):
        cache = {'fetched_at': 100.0}
        self.assertTrue(store_client.is_cache_fresh(cache, 100 + 3600, max_age_seconds=86400))

    def test_stale_beyond_max_age(self):
        cache = {'fetched_at': 0.0}
        self.assertFalse(store_client.is_cache_fresh(cache, 86401, max_age_seconds=86400))


class TestGetIndex(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.tmpdir, 'cache.json')

    def test_uses_fresh_cache_without_fetching(self):
        store_client.save_cache(self.cache_path, {
            'generated_at': 'cached', 'entries': [], 'fetched_at': 1000.0,
        })
        calls = []

        def _fetch(url):
            calls.append(url)
            return SAMPLE_RAW_INDEX

        result = store_client.get_index(
            _fetch, cache_path=self.cache_path, now=1000.0 + 60)
        self.assertEqual(result['generated_at'], 'cached')
        self.assertEqual(calls, [])

    def test_fetches_and_caches_when_stale(self):
        store_client.save_cache(self.cache_path, {
            'generated_at': 'old', 'entries': [], 'fetched_at': 0.0,
        })
        result = store_client.get_index(
            lambda url: SAMPLE_RAW_INDEX, cache_path=self.cache_path,
            now=store_client.DEFAULT_CACHE_MAX_AGE_SECONDS + 1)
        self.assertEqual(len(result['entries']), 2)
        # Persisted for next call.
        self.assertEqual(store_client.load_cache(self.cache_path)['generated_at'],
                          '2026-08-19T00:00:00+00:00')

    def test_force_refresh_bypasses_fresh_cache(self):
        store_client.save_cache(self.cache_path, {
            'generated_at': 'cached', 'entries': [], 'fetched_at': 1000.0,
        })
        result = store_client.get_index(
            lambda url: SAMPLE_RAW_INDEX, cache_path=self.cache_path,
            now=1000.0 + 60, force_refresh=True)
        self.assertEqual(result['generated_at'], '2026-08-19T00:00:00+00:00')

    def test_falls_back_to_stale_cache_on_network_failure(self):
        store_client.save_cache(self.cache_path, {
            'generated_at': 'old-but-something', 'entries': [], 'fetched_at': 0.0,
        })

        def _boom(url):
            raise OSError('offline')

        result = store_client.get_index(
            _boom, cache_path=self.cache_path,
            now=store_client.DEFAULT_CACHE_MAX_AGE_SECONDS + 1)
        self.assertEqual(result['generated_at'], 'old-but-something')

    def test_returns_empty_catalogue_when_nothing_available(self):
        def _boom(url):
            raise OSError('offline')

        result = store_client.get_index(_boom, cache_path=self.cache_path, now=0)
        self.assertEqual(result['entries'], [])


class TestEntriesById(unittest.TestCase):
    def test_indexes_by_id(self):
        index = {'entries': [{'id': 'a.b', 'name': 'A'}, {'id': 'c.d', 'name': 'C'}]}
        result = store_client.entries_by_id(index)
        self.assertEqual(result['a.b']['name'], 'A')
        self.assertEqual(set(result), {'a.b', 'c.d'})


class TestEntriesByCategory(unittest.TestCase):
    def test_groups_preserving_order(self):
        index = {'entries': [
            {'id': 'a', 'category': 'svod'},
            {'id': 'b', 'category': 'replay'},
            {'id': 'c', 'category': 'svod'},
        ]}
        grouped = store_client.entries_by_category(index)
        self.assertEqual([e['id'] for e in grouped['svod']], ['a', 'c'])
        self.assertEqual([e['id'] for e in grouped['replay']], ['b'])

    def test_missing_category_falls_back_to_autre(self):
        index = {'entries': [{'id': 'a'}]}
        grouped = store_client.entries_by_category(index)
        self.assertEqual(list(grouped), ['autre'])


class TestSearchEntries(unittest.TestCase):
    def setUp(self):
        self.index = SAMPLE_RAW_INDEX

    def test_empty_query_returns_all(self):
        result = store_client.search_entries(self.index, '')
        self.assertEqual(len(result), 2)

    def test_matches_name_case_insensitive(self):
        result = store_client.search_entries(self.index, 'NETFLIX')
        self.assertEqual([e['id'] for e in result], ['video.netflix'])

    def test_matches_description(self):
        result = store_client.search_entries(self.index, 'televisions')
        self.assertEqual([e['id'] for e in result], ['tv.francetv'])

    def test_no_match_returns_empty(self):
        result = store_client.search_entries(self.index, 'nonexistent')
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
