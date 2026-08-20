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
