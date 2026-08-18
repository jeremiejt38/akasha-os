"""Unit tests for local_cache.py — no xbmc dependency."""

import os
import tempfile
import unittest

from local_cache import LocalCache, page_cache_key


class TestLocalCache(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.cache = LocalCache(self.db_path)

    def tearDown(self):
        os.remove(self.db_path)

    def test_get_missing_key_returns_none(self):
        self.assertIsNone(self.cache.get('nope'))

    def test_set_then_get_roundtrips_json_value(self):
        self.cache.set('key1', {'a': 1, 'b': [1, 2, 3]}, ttl_seconds=60)
        self.assertEqual(self.cache.get('key1'), {'a': 1, 'b': [1, 2, 3]})

    def test_expired_entry_returns_none(self):
        self.cache.set('key1', {'a': 1}, ttl_seconds=-10)
        self.assertIsNone(self.cache.get('key1'))

    def test_set_overwrites_existing_key(self):
        self.cache.set('key1', {'v': 1}, ttl_seconds=60)
        self.cache.set('key1', {'v': 2}, ttl_seconds=60)
        self.assertEqual(self.cache.get('key1'), {'v': 2})

    def test_get_or_set_computes_once_on_miss(self):
        calls = []

        def compute():
            calls.append(1)
            return {'computed': True}

        result1 = self.cache.get_or_set('key1', 60, compute)
        result2 = self.cache.get_or_set('key1', 60, compute)

        self.assertEqual(result1, {'computed': True})
        self.assertEqual(result2, {'computed': True})
        self.assertEqual(len(calls), 1)

    def test_page_cache_key_joins_parts(self):
        self.assertEqual(page_cache_key('sections', '7', 'all', 0, 30), 'sections:7:all:0:30')

    def test_page_cache_key_skips_none_and_empty(self):
        self.assertEqual(page_cache_key('a', None, '', 'b'), 'a:b')


if __name__ == '__main__':
    unittest.main()
