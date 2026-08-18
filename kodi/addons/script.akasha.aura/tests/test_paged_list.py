"""Unit tests for paged_list.py — no xbmc dependency."""

import unittest

from paged_list import PagedList


def make_fetcher(total_items, calls_log=None):
    """Return a fetch_page(offset, limit) callable over a fake dataset."""
    dataset = ['item-{}'.format(i) for i in range(total_items)]

    def fetch_page(offset, limit):
        if calls_log is not None:
            calls_log.append((offset, limit))
        return dataset[offset:offset + limit]

    return fetch_page


class TestPagedList(unittest.TestCase):
    def test_load_initial_fetches_one_page(self):
        calls = []
        pl = PagedList(make_fetcher(100, calls), page_size=30, prefetch_margin=15)

        loaded = pl.load_initial()

        self.assertEqual(len(loaded), 30)
        self.assertEqual(len(pl.items), 30)
        self.assertEqual(calls, [(0, 30)])
        self.assertFalse(pl.exhausted)

    def test_maybe_load_more_triggers_within_prefetch_margin(self):
        pl = PagedList(make_fetcher(100), page_size=30, prefetch_margin=15)
        pl.load_initial()

        # Position 14 is still 16 away from the end (30) -> no fetch yet.
        loaded = pl.maybe_load_more(14)
        self.assertEqual(loaded, [])
        self.assertEqual(len(pl.items), 30)

        # Position 15 is within the 15-item margin of the loaded end (30).
        loaded = pl.maybe_load_more(15)
        self.assertEqual(len(loaded), 30)
        self.assertEqual(len(pl.items), 60)

    def test_maybe_load_more_does_nothing_once_exhausted(self):
        calls = []
        pl = PagedList(make_fetcher(10, calls), page_size=30, prefetch_margin=15)
        pl.load_initial()

        self.assertTrue(pl.exhausted)
        self.assertEqual(len(pl.items), 10)

        loaded = pl.maybe_load_more(9)
        self.assertEqual(loaded, [])
        self.assertEqual(calls, [(0, 30)])  # no extra fetch attempted

    def test_short_final_page_marks_exhausted(self):
        pl = PagedList(make_fetcher(35), page_size=30, prefetch_margin=15)
        pl.load_initial()
        self.assertFalse(pl.exhausted)

        pl.maybe_load_more(15)
        self.assertEqual(len(pl.items), 35)
        self.assertTrue(pl.exhausted)

    def test_empty_dataset(self):
        pl = PagedList(make_fetcher(0), page_size=30, prefetch_margin=15)
        loaded = pl.load_initial()
        self.assertEqual(loaded, [])
        self.assertTrue(pl.exhausted)


if __name__ == '__main__':
    unittest.main()
