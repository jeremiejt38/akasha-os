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

    def test_get_stale_returns_expired_row_flagged(self):
        self.cache.set('key1', {'v': 1}, ttl_seconds=-10)
        value, expired = self.cache.get_stale('key1')
        self.assertEqual(value, {'v': 1})
        self.assertTrue(expired)

    def test_get_stale_marks_fresh_row_not_expired(self):
        self.cache.set('key1', {'v': 1}, ttl_seconds=60)
        value, expired = self.cache.get_stale('key1')
        self.assertEqual(value, {'v': 1})
        self.assertFalse(expired)

    def test_get_stale_missing_key(self):
        self.assertEqual(self.cache.get_stale('nope'), (None, True))

    def test_wal_mode_enabled(self):
        conn = sqlite3.connect(self.db_path)
        mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
        conn.close()
        self.assertEqual(mode, 'wal')

    def test_expired_rows_purged_on_write_when_due(self):
        self.cache.set('old', {'v': 1}, ttl_seconds=-10)
        self.cache._next_purge = 0  # force the opportunistic purge
        self.cache.set('new', {'v': 2}, ttl_seconds=60)
        conn = sqlite3.connect(self.db_path)
        keys = [r[0] for r in conn.execute('SELECT key FROM cache')]
        conn.close()
        self.assertNotIn('old', keys)
        self.assertIn('new', keys)

    def test_concurrent_readers_and_writer(self):
        import threading

        errors = []

        def writer():
            try:
                for i in range(30):
                    self.cache.set('k%d' % (i % 5), {'i': i}, ttl_seconds=60)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(30):
                    self.cache.get('k%d' % (i % 5))
                    self.cache.get_stale('k%d' % (i % 5))
            except Exception as e:
                errors.append(e)

        threads = ([threading.Thread(target=writer)] +
                   [threading.Thread(target=reader) for _ in range(4)])
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_non_schema_operational_error_is_a_miss_not_an_exception(self):
        # 'no such table' self-heals; any other OperationalError (locked
        # db, corrupt file...) must still degrade to a miss, not raise.
        from unittest import mock

        conn = mock.MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError('database is locked')
        with mock.patch.object(self.cache, '_connect', return_value=conn):
            self.assertIsNone(self.cache.get('key1'))
            self.assertEqual(self.cache.get_stale('key1'), (None, True))
            self.cache.set('key1', {'v': 1})  # silently skipped, no raise


if __name__ == '__main__':
    unittest.main()
