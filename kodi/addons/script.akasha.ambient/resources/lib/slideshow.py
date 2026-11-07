"""Akasha Ambient — photo cycling and Ken Burns variant selection.

Pure logic (stdlib only, no `xbmc*`) so it is unit-testable. The window
(ambient_window.py) owns the two skin image slots; this module only decides
*which* photo(s) come next and which Ken Burns variant drives them, keeping
the order shuffled without ever repeating the same photo twice in a row
across cycle boundaries — the Google TV Ambient Mode feel, where the
slideshow is random but never stutters on the same frame.

Frames: `next_frame()` returns a list of 1 or 2 paths. When portrait
pairing is enabled and two consecutive queued photos are both portrait,
they are shown side-by-side in a single frame — the way Google TV pairs
vertical shots instead of pillarboxing them.

Ken Burns variants are skin-side: Ambient.xml defines conditioned
`Visible`/`Hidden` zoom animations per `ambient.kb{slot}` value, because
Kodi animation start/end values cannot be dynamic (see
docs/ambient-mode/decisions.md). Variants:

- 1: slow zoom in, screen center
- 2: slow zoom out, screen center
- 3: slow zoom in drifting toward the top-left quarter
- 4: slow zoom in drifting toward the bottom-right quarter
"""
import random

KB_VARIANTS = ('1', '2', '3', '4')


class PhotoCycler:
    """Yield photo frames in a shuffled order that never repeats back-to-back.

    When the queue is exhausted it is rebuilt from the full path list and
    reshuffled; if the first photo of the new cycle would equal the last
    photo shown, it is swapped with the next entry so a boundary never
    displays the same frame twice in a row.

    `size_fn` (path -> (w, h) or None) enables portrait pairing: with
    `pair_portraits=True`, `next_frame()` groups two consecutive portrait
    photos into one frame.
    """

    def __init__(self, paths, rng=None, size_fn=None, pair_portraits=False):
        self._paths = list(paths)
        self._rng = rng or random
        self._size_fn = size_fn
        self._pair_portraits = pair_portraits and callable(size_fn)
        self._queue = []
        self._last = None

    def __len__(self):
        return len(self._paths)

    def _dequeue(self):
        if not self._queue:
            self._queue = list(self._paths)
            self._rng.shuffle(self._queue)
            if len(self._queue) > 1 and self._queue[0] == self._last:
                self._queue[0], self._queue[1] = self._queue[1], self._queue[0]
        self._last = self._queue.pop(0)
        return self._last

    def _is_portrait(self, path):
        size = self._size_fn(path)
        return bool(size and size[1] > size[0])

    def next_photo(self):
        """Return the next photo path, or None when no photos exist."""
        if not self._paths:
            return None
        return self._dequeue()

    def next_frame(self):
        """Return the next frame as a list of 1-2 photo paths.

        Pairs two consecutive portraits when pairing is enabled; otherwise
        equivalent to wrapping `next_photo()` in a list.
        """
        if not self._paths:
            return None
        first = self._dequeue()
        if not self._pair_portraits or not self._is_portrait(first):
            return [first]
        if not self._queue:
            # First of a fresh cycle: refill so we can peek at the next photo.
            self._queue = list(self._paths)
            self._rng.shuffle(self._queue)
            if len(self._queue) > 1 and self._queue[0] == self._last:
                self._queue[0], self._queue[1] = self._queue[1], self._queue[0]
        if not self._queue or not self._is_portrait(self._queue[0]):
            return [first]
        second = self._dequeue()
        return [first, second]

    def next_variant(self):
        """Return a random Ken Burns variant id ('1'..'4')."""
        return self._rng.choice(KB_VARIANTS)
