"""Unit tests for local_cache.py — no xbmc dependency."""

import os
import sqlite3
import tempfile
import unittest

from local_cache import LocalCache, get_or_set_page, page_cache_key


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

    def test_get_self_heals_when_table_is_missing(self):
        """Regression test: found on a real device where the sqlite file
        ended up without its table ('no such table: cache') after an
        external process interfered with it while Kodi still held the
        LocalCache instance -- get()/set() must never propagate this as a
        hard failure since the cache is a pure optimisation layer."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('DROP TABLE cache')
        conn.commit()
        conn.close()

        self.assertIsNone(self.cache.get('key1'))  # self-heals, treated as a miss

    def test_set_self_heals_when_table_is_missing(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('DROP TABLE cache')
        conn.commit()
        conn.close()

        self.cache.set('key1', {'v': 1}, ttl_seconds=60)

        self.assertEqual(self.cache.get('key1'), {'v': 1})

    def test_page_cache_key_joins_parts(self):
        self.assertEqual(page_cache_key('sections', '7', 'all', 0, 30), 'sections:7:all:0:30')

    def test_page_cache_key_skips_none_and_empty(self):
        self.assertEqual(page_cache_key('a', None, '', 'b'), 'a:b')

    def test_get_or_set_page_preserves_tuple_across_a_cache_hit(self):
        """Regression test: a JSON cache round-trips a tuple as a list, which
        would otherwise make PagedList treat a whole (items, total) result
        as a single page on the second (cached) call -- found on a real
        device where every paginated view silently became '2 element(s)'."""
        calls = []

        def compute():
            calls.append(1)
            return ([{'title': 'A'}, {'title': 'B'}], 437)

        items1, total1 = get_or_set_page(self.cache, 'key1', 60, compute)
        items2, total2 = get_or_set_page(self.cache, 'key1', 60, compute)

        self.assertEqual(items1, [{'title': 'A'}, {'title': 'B'}])
        self.assertEqual(total1, 437)
        self.assertEqual(items1, items2)
        self.assertEqual(total1, total2)
        self.assertEqual(len(calls), 1)  # second call was a cache hit

    def test_get_or_set_page_handles_plain_list_without_total(self):
        def compute():
            return [{'title': 'A'}]

        items1, total1 = get_or_set_page(self.cache, 'key2', 60, compute)
        items2, total2 = get_or_set_page(self.cache, 'key2', 60, compute)

        self.assertEqual(items1, [{'title': 'A'}])
        self.assertIsNone(total1)
        self.assertEqual(items1, items2)
        self.assertIsNone(total2)


if __name__ == '__main__':
    unittest.main()
