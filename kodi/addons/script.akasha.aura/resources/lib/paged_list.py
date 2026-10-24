"""Akasha Aura — incremental ("infinite scroll") loading helper.

Loading an entire Plex library/hub upfront (hundreds of items, each with a
poster) is unnecessarily heavy on a Raspberry Pi. `PagedList` fetches a first
page eagerly, then fetches the next page only once the user's selection gets
within `prefetch_margin` items of the end of what's already loaded --
mirroring how Netflix/Plex-style UIs lazy-load rows and grids.

Per plan a3f9c2e1 (see docs/aura/decisions.md): the real total item count
must be shown immediately, not just "how many are loaded so far". Plex
already includes this total in every paginated response at no extra
request cost, so `fetch_page` may optionally return it alongside the page
itself -- see the `(items, total)` tuple form below -- instead of Akasha
issuing a separate "count" request.

No dependency on xbmc*, testable with plain `python3 -m unittest`.
"""

DEFAULT_PAGE_SIZE = 30
DEFAULT_PREFETCH_MARGIN = 15


class PagedList:
    """Incrementally loads items from `fetch_page(offset, limit)`.

    `fetch_page` is called with an `offset` (how many items already loaded)
    and a `limit` (page size). It must return either:
    - a plain list of items for that page (shorter than `limit`, or empty,
      once there is nothing left to load), or
    - a `(items, total)` tuple, where `total` is the real total number of
      items available (from the source's own pagination metadata), used to
      populate `self.total` so callers can display it immediately instead of
      only "however many are loaded so far".
    """

    def __init__(self, fetch_page, page_size=DEFAULT_PAGE_SIZE,
                 prefetch_margin=DEFAULT_PREFETCH_MARGIN, max_items=None):
        self.fetch_page = fetch_page
        self.page_size = page_size
        self.prefetch_margin = prefetch_margin
        self.max_items = max_items
        self.items = []
        self.exhausted = False
        self.total = None

    def load_initial(self):
        """Fetch the first page. Returns the newly-loaded items."""
        return self._load_next_page()

    def maybe_load_more(self, selected_position):
        """If `selected_position` is near the loaded end, fetch another page.

        Returns the newly-loaded items (possibly empty if nothing was
        fetched, either because we're not close enough to the end yet, or
        because the list is already exhausted).
        """
        if self.exhausted:
            return []
        if selected_position < len(self.items) - self.prefetch_margin:
            return []
        return self._load_next_page()

    def _load_next_page(self):
        if self.max_items is not None and len(self.items) >= self.max_items:
            self.exhausted = True
            return []
        result = self.fetch_page(len(self.items), self.page_size)
        if isinstance(result, tuple):
            page, total = result
        else:
            page, total = result, None
        page = page or []
        if total is not None:
            self.total = total
        if self.max_items is not None and len(self.items) + len(page) >= self.max_items:
            page = page[:max(0, self.max_items - len(self.items))]
            self.exhausted = True
        self.items.extend(page)
        if len(page) < self.page_size:
            self.exhausted = True
            if self.total is None:
                self.total = len(self.items)
        return page


def series_dedup_key(item):
    """Identity key that collapses a show's episodes/seasons into one card.

    Plex recommendation rows can be episode- or season-level (recently
    added TV, on-deck), so one added season floods the row with 15
    identical show posters. Plex's own clients group these by series --
    this key yields the same card identity for every item of the show,
    and also merges exact duplicates (same rating_key) Plex sometimes
    emits in mixed hubs. Items without a key stay unique.
    """
    if item.get('type') == 'episode':
        return item.get('grandparent_rating_key') or item.get('rating_key')
    if item.get('type') == 'season':
        return item.get('parent_rating_key') or item.get('rating_key')
    return item.get('rating_key') or id(item)


def dedup_fetch(fetch_page, raw_page_size=32, max_raw_fetches=5):
    """Wrap `fetch_page` so each series appears once in the paged row.

    The wrapper owns the raw stream position: PagedList offsets count
    deduped items, so the raw offset must be tracked separately. It keeps
    fetching raw pages until it has `limit` unique items (or the raw
    stream ends), so a short returned page still means "exhausted" to
    PagedList semantics.

    Raw exhaustion: a *short page is not* the end -- a hub's inline page
    is shorter than the raw page size yet continues through its `key`
    endpoint. The stream is done when the source reports a total we've
    reached, or a raw page comes back empty. `total` is dropped -- the
    true deduped count cannot be known without draining the stream.
    `max_raw_fetches` caps requests per call on pathological hubs.
    """
    seen = set()
    state = {'offset': 0, 'done': False, 'total': None}

    def fetch(offset, limit):
        batch = []
        fetches = 0
        while len(batch) < limit and not state['done'] \
                and fetches < max_raw_fetches:
            result = fetch_page(state['offset'], raw_page_size)
            fetches += 1
            page, total = (result if isinstance(result, tuple)
                           else (result, None))
            page = page or []
            state['offset'] += len(page)
            if total is not None:
                state['total'] = total
            if not page or (total is not None and state['offset'] >= total):
                state['done'] = True
            for item in page:
                key = series_dedup_key(item)
                if key in seen:
                    continue
                seen.add(key)
                batch.append(item)
                if len(batch) >= limit:
                    break
        # The raw total is an upper bound for the deduped count -- enough
        # for end-of-row placeholders (extras drop when the stream ends).
        return batch, state['total']

    return fetch
