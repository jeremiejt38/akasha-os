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

import threading
import time

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
        # Serializes fetches and arms the async prefetch worker -- two
        # overlapping page loads would race on `self.items` offsets.
        self._fetch_lock = threading.Lock()
        self._inflight = False
        self._inflight_lock = threading.Lock()
        # A scroll prefetch that arms before load_initial() lands would
        # race the first fill (page 2 rendered, then repainted over).
        self._initial_loaded = False
        # Failed fetches back off exponentially so an offline path does
        # not burn a WAN request on every subsequent keypress.
        self._retry_after = 0.0
        self._retry_delay = 5.0

    def load_initial(self):
        """Fetch the first page. Returns the newly-loaded items."""
        page = self._load_next_page()
        self._initial_loaded = True
        return page

    def _ready_for_prefetch(self):
        """Exhaustion/first-page/retry gate shared by both load paths."""
        if not self._initial_loaded or self.exhausted:
            return False
        return time.monotonic() >= self._retry_after

    def _note_fetch_error(self):
        self._retry_after = time.monotonic() + self._retry_delay
        self._retry_delay = min(30.0, self._retry_delay * 2)

    def maybe_load_more(self, selected_position):
        """If `selected_position` is near the loaded end, fetch another page.

        Returns the newly-loaded items (possibly empty if nothing was
        fetched, either because we're not close enough to the end yet, or
        because the list is already exhausted). Blocks the caller for the
        duration of the network fetch -- GUI-driven callers should prefer
        `prefetch_async` so input handling is never stalled by latency.
        """
        if selected_position < len(self.items) - self.prefetch_margin:
            return []
        with self._inflight_lock:
            if self._inflight or not self._ready_for_prefetch():
                return []
            self._inflight = True
        try:
            return self._load_next_page()
        except Exception:
            self._note_fetch_error()
            raise
        finally:
            self._inflight = False

    def prefetch_async(self, selected_position, on_page, on_error=None):
        """Non-blocking `maybe_load_more` for input-driven callers.

        If `selected_position` is near the loaded end and no fetch is
        already in flight, a daemon thread fetches the next page and then
        invokes `on_page(new_items)` **on the worker thread**. The
        callback must not touch Kodi GUI objects: callers should stash
        the page and render it from the next input event -- the prefetch
        margin leaves plenty of loaded items to scroll through meanwhile.
        `on_error(exception)` is invoked instead when the fetch raises.
        """
        if selected_position < len(self.items) - self.prefetch_margin:
            return
        with self._inflight_lock:
            if self._inflight or not self._ready_for_prefetch():
                return
            self._inflight = True

        def work():
            try:
                page = self._load_next_page()
                if page and on_page:
                    on_page(page)
            except Exception as e:
                self._note_fetch_error()
                if on_error:
                    on_error(e)
            finally:
                self._inflight = False

        threading.Thread(target=work, daemon=True).start()

    def _load_next_page(self):
        with self._fetch_lock:
            if self.max_items is not None and len(self.items) >= self.max_items:
                self.exhausted = True
                return []
            result = self.fetch_page(len(self.items), self.page_size)
            self._retry_after = 0.0
            self._retry_delay = 5.0
            done = None
            if isinstance(result, tuple):
                if len(result) >= 3:
                    page, total, done = result[0], result[1], result[2]
                else:
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
                # `done is False` = the wrapper hit its raw-fetch budget,
                # not the end of the stream -- the row continues on the
                # next call instead of being silently truncated.
                if done is not False:
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
    stream ends). A short returned page therefore comes back with
    `done=False` so PagedList keeps paginating instead of silently
    truncating the row when the raw-fetch cap is hit.

    Raw exhaustion: a *short page is not* the end -- a hub's inline page
    is shorter than the raw page size yet continues through its `key`
    endpoint. The stream is done when the source reports a total we've
    reached, or a raw page comes back empty. `total` is dropped -- the
    true deduped count cannot be known without draining the stream.
    `max_raw_fetches` caps requests per call on pathological hubs.
    """
    seen = set()
    state = {'offset': 0, 'done': False, 'total': None, 'backlog': []}

    def fetch(offset, limit):
        batch = []
        # Overflow from a previous call's raw page comes first -- raw
        # offsets already advanced past it, so dropping it would lose
        # items permanently.
        while len(batch) < limit and state['backlog']:
            batch.append(state['backlog'].pop(0))
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
                if len(batch) < limit:
                    batch.append(item)
                else:
                    state['backlog'].append(item)
        # The raw total is an upper bound for the deduped count -- enough
        # for end-of-row placeholders (extras drop when the stream ends).
        # Third element tells PagedList whether the stream really ended;
        # hitting `max_raw_fetches` with a short batch -- or a backlog
        # still pending -- is NOT exhaustion.
        return batch, state['total'], \
            state['done'] and not state['backlog']

    return fetch
