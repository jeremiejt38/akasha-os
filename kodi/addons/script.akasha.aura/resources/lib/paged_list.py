"""Akasha Aura — incremental ("infinite scroll") loading helper.

Loading an entire Plex library/hub upfront (hundreds of items, each with a
poster) is unnecessarily heavy on a Raspberry Pi. `PagedList` fetches a first
page eagerly, then fetches the next page only once the user's selection gets
within `prefetch_margin` items of the end of what's already loaded --
mirroring how Netflix/Plex-style UIs lazy-load rows and grids.

No dependency on xbmc*, testable with plain `python3 -m unittest`.
"""

DEFAULT_PAGE_SIZE = 30
DEFAULT_PREFETCH_MARGIN = 15


class PagedList:
    """Incrementally loads items from `fetch_page(offset, limit) -> list`.

    `fetch_page` is called with an `offset` (how many items already loaded)
    and a `limit` (page size), and must return a list of items for that page
    (shorter than `limit`, or empty, once there is nothing left to load).
    """

    def __init__(self, fetch_page, page_size=DEFAULT_PAGE_SIZE,
                 prefetch_margin=DEFAULT_PREFETCH_MARGIN):
        self.fetch_page = fetch_page
        self.page_size = page_size
        self.prefetch_margin = prefetch_margin
        self.items = []
        self.exhausted = False

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
        page = self.fetch_page(len(self.items), self.page_size) or []
        self.items.extend(page)
        if len(page) < self.page_size:
            self.exhausted = True
        return page
