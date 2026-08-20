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


def make_fetcher_with_total(total_items, fake_total, calls_log=None):
    """Return a fetch_page(offset, limit) callable that returns (page, fake_total) tuples."""
    dataset = ['item-{}'.format(i) for i in range(total_items)]

    def fetch_page(offset, limit):
        if calls_log is not None:
            calls_log.append((offset, limit))
        return dataset[offset:offset + limit], fake_total

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


class TestPagedListMaxItems(unittest.TestCase):
    """max_items caps how much a row/list will ever load, regardless of how
    many the source actually has -- used to keep Recommande's rows bounded
    (plan feedback: max 100 items per row)."""

    def test_caps_a_single_page_that_overshoots(self):
        pl = PagedList(make_fetcher(1000), page_size=150, prefetch_margin=15, max_items=100)
        loaded = pl.load_initial()
        self.assertEqual(len(loaded), 100)
        self.assertEqual(len(pl.items), 100)
        self.assertTrue(pl.exhausted)

    def test_caps_across_multiple_pages(self):
        calls = []
        pl = PagedList(make_fetcher(1000, calls), page_size=30, prefetch_margin=15, max_items=100)
        pl.load_initial()
        while not pl.exhausted:
            pl.maybe_load_more(len(pl.items) - 1)
        self.assertEqual(len(pl.items), 100)
        self.assertTrue(pl.exhausted)

    def test_no_further_fetch_once_cap_reached(self):
        calls = []
        pl = PagedList(make_fetcher(1000, calls), page_size=50, prefetch_margin=15, max_items=100)
        pl.load_initial()
        pl.maybe_load_more(49)
        self.assertEqual(len(pl.items), 100)
        calls_before = len(calls)
        pl.maybe_load_more(99)
        self.assertEqual(len(calls), calls_before)  # no extra fetch attempted

    def test_max_items_larger_than_dataset_is_a_noop(self):
        pl = PagedList(make_fetcher(10), page_size=30, prefetch_margin=15, max_items=100)
        pl.load_initial()
        self.assertEqual(len(pl.items), 10)
        self.assertTrue(pl.exhausted)

    def test_unset_max_items_is_unbounded(self):
        pl = PagedList(make_fetcher(1000), page_size=100, prefetch_margin=15)
        pl.load_initial()
        self.assertEqual(len(pl.items), 100)
        self.assertFalse(pl.exhausted)


class TestPagedListTotal(unittest.TestCase):
    def test_total_is_none_before_any_load(self):
        pl = PagedList(make_fetcher(100), page_size=30, prefetch_margin=15)
        self.assertIsNone(pl.total)

    def test_total_populated_from_tuple_on_first_page(self):
        pl = PagedList(make_fetcher_with_total(100, 437), page_size=30, prefetch_margin=15)
        pl.load_initial()
        self.assertEqual(pl.total, 437)
        self.assertEqual(len(pl.items), 30)

    def test_total_updated_on_subsequent_pages(self):
        pl = PagedList(make_fetcher_with_total(100, 437), page_size=30, prefetch_margin=15)
        pl.load_initial()
        pl.maybe_load_more(15)
        self.assertEqual(pl.total, 437)
        self.assertEqual(len(pl.items), 60)

    def test_total_falls_back_to_loaded_count_when_never_provided(self):
        pl = PagedList(make_fetcher(10), page_size=30, prefetch_margin=15)
        pl.load_initial()
        self.assertTrue(pl.exhausted)
        self.assertEqual(pl.total, 10)

    def test_total_none_while_not_exhausted_and_never_provided(self):
        pl = PagedList(make_fetcher(100), page_size=30, prefetch_margin=15)
        pl.load_initial()
        self.assertFalse(pl.exhausted)
        self.assertIsNone(pl.total)


if __name__ == '__main__':
    unittest.main()
