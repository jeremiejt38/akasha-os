"""Unit tests for paged_list.py — no xbmc dependency."""

import unittest

from paged_list import PagedList, dedup_fetch, series_dedup_key


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


def ep(show_key, ep_key):
    return {'type': 'episode', 'rating_key': ep_key,
            'grandparent_rating_key': show_key}


def show(key):
    return {'type': 'show', 'rating_key': key}


class TestSeriesDedupKey(unittest.TestCase):
    """Episodes and seasons collapse to their show's card identity."""

    def test_episodes_of_one_show_share_a_key(self):
        self.assertEqual(series_dedup_key(ep('100', 'e1')),
                         series_dedup_key(ep('100', 'e2')))

    def test_different_shows_differ(self):
        self.assertNotEqual(series_dedup_key(ep('100', 'e1')),
                            series_dedup_key(ep('200', 'e1')))

    def test_season_collapses_to_show(self):
        item = {'type': 'season', 'rating_key': 's1',
                'parent_rating_key': '100'}
        self.assertEqual(series_dedup_key(item), '100')

    def test_movie_and_show_keep_their_own_key(self):
        self.assertEqual(series_dedup_key(show('100')), '100')
        self.assertEqual(
            series_dedup_key({'type': 'movie', 'rating_key': 'm1'}), 'm1')

    def test_episode_matches_its_show(self):
        # A hub emitting both the show and its episodes collapses to one
        # card: grandparent_rating_key == show rating_key.
        self.assertEqual(series_dedup_key(ep('100', 'e1')),
                         series_dedup_key(show('100')))


class TestDedupFetch(unittest.TestCase):
    def test_collapses_a_season_dump_to_one_card(self):
        dataset = [ep('100', 'e%d' % i) for i in range(12)] + \
                  [show('200'), ep('300', 'e1')]
        calls = []

        def fetch(offset, limit):
            calls.append((offset, limit))
            return dataset[offset:offset + limit], len(dataset)

        wrapped = dedup_fetch(fetch)
        page, _, _ = wrapped(0, 10)
        self.assertEqual([series_dedup_key(i) for i in page],
                         ['100', '200', '300'])

    def test_stream_continues_past_inline_page(self):
        # A short inline page (25 < 32 raw size) is NOT the end when the
        # source keeps returning items -- the real hub fetch_page behaves
        # this way for keyed hubs.
        dataset = ([ep('100', 'e%d' % i) for i in range(25)] +
                   [show('s%d' % i) for i in range(40)])

        def fetch(offset, limit):
            page = dataset[offset:offset + limit]
            return page, (len(dataset) if offset >= 25 else None)

        wrapped = dedup_fetch(fetch, raw_page_size=32)
        page, _, _ = wrapped(0, 10)
        # 1 unique episode + 9 shows -> stream continued past the inline.
        self.assertEqual(len(page), 10)
        self.assertEqual(page[0]['rating_key'], 'e0')

    def test_exhaustion_on_empty_raw_page(self):
        dataset = [show('s1'), ep('100', 'e1'), ep('100', 'e2')]

        def fetch(offset, limit):
            return dataset[offset:offset + limit], len(dataset)

        wrapped = dedup_fetch(fetch, raw_page_size=8)
        page, _, _ = wrapped(0, 10)
        self.assertEqual(len(page), 2)

    def test_max_raw_fetches_caps_requests(self):
        calls = []

        def fetch(offset, limit):
            calls.append(offset)
            return [ep('100', 'e%d' % offset)], None  # infinite dupes

        wrapped = dedup_fetch(fetch, raw_page_size=32, max_raw_fetches=3)
        page, _, _ = wrapped(0, 10)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(page), 1)

    def test_short_page_from_fetch_cap_does_not_exhaust(self):
        # 3 raw fetches of all-dupes produce a 1-item batch while the
        # stream still has unique shows behind -- `done=False` must keep
        # the PagedList paginating instead of truncating the row.
        dataset = [ep('100', 'e%d' % i) for i in range(20)] + \
                  [show('s%d' % i) for i in range(40)]

        def fetch(offset, limit):
            return dataset[offset:offset + limit], len(dataset)

        pl = PagedList(dedup_fetch(fetch, raw_page_size=4, max_raw_fetches=3),
                       page_size=10, prefetch_margin=3)
        pl.load_initial()
        # First call: 12 raw items read, all collapse to one card ->
        # short page (1 < 10) but the stream is not done.
        self.assertFalse(pl.exhausted)
        while not pl.exhausted:
            pl.maybe_load_more(len(pl.items) - 1)
        # The whole unique stream eventually surfaces: 1 show card for
        # the episodes + 40 real shows.
        self.assertEqual(len(pl.items), 41)

    def test_integrates_with_paged_list(self):
        dataset = [ep('100', 'e%d' % i) for i in range(20)] + \
                  [show('s%d' % i) for i in range(60)]

        def fetch(offset, limit):
            page = dataset[offset:offset + limit]
            return page, len(dataset)

        pl = PagedList(dedup_fetch(fetch), page_size=10, prefetch_margin=3)
        pl.load_initial()
        keys = [series_dedup_key(i) for i in pl.items]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(pl.items), 10)
        # One episode card + nine show cards.
        self.assertEqual(keys, ['100'] + ['s%d' % i for i in range(9)])


if __name__ == '__main__':
    unittest.main()
