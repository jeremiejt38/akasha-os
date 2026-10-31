"""Unit tests for gui_guard.py — the _ui_lock serialization contract.

gui_guard reads a window's `_ui_lock` and serializes selection reads
against worker-side list rebuilds (the reset()-vs-getSelectedPosition
SEGV class). These tests pin down the contract: a busy lock degrades to
the benign value instead of blocking input, a free/absent lock changes
nothing, and same-thread re-entrance (guarded call inside a locked
render tail) never deadlocks or fails.
"""

import os
import sys
import threading
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

sys.modules.setdefault('xbmcgui', types.ModuleType('xbmcgui'))

import gui_guard  # noqa: E402


class FakeControl:
    def __init__(self, size=5, selected=2):
        self._size = size
        self._selected = selected
        self.item = object()

    def size(self):
        return self._size

    def getSelectedPosition(self):
        return self._selected

    def getSelectedItem(self):
        return self.item

    def selectItem(self, position):
        self._selected = position


class FakeWindow:
    def __init__(self, control=None, with_lock=True):
        self._control = control
        if with_lock:
            self._ui_lock = threading.RLock()

    def getControl(self, cid):
        return self._control

    def setFocus(self, control):
        self.focused = control


class TestGuiGuardLock(unittest.TestCase):
    def test_busy_lock_degrades_to_benign_values(self):
        win = FakeWindow(FakeControl())
        acquired = threading.Event()
        release = threading.Event()

        def holder():
            with win._ui_lock:
                acquired.set()
                release.wait(5)

        t = threading.Thread(target=holder)
        t.start()
        acquired.wait(5)
        try:
            self.assertEqual(gui_guard.selpos(win, 100), -1)
            self.assertIsNone(gui_guard.selitem(win, 100))
            self.assertFalse(gui_guard.select(win, 100, 0))
            self.assertFalse(gui_guard.focus(win, 100))
        finally:
            release.set()
            t.join()

    def test_free_lock_passes_through_normally(self):
        control = FakeControl()
        win = FakeWindow(control)
        self.assertEqual(gui_guard.selpos(win, 100), 2)
        self.assertIs(gui_guard.selitem(win, 100), control.item)
        self.assertTrue(gui_guard.select(win, 100, 4))
        self.assertTrue(gui_guard.focus(win, 100))

    def test_lock_released_after_call(self):
        win = FakeWindow(FakeControl())
        gui_guard.selpos(win, 100)
        # A second acquisition must succeed immediately -- the lock was
        # not left held by the guarded call.
        self.assertTrue(win._ui_lock.acquire(blocking=False))
        win._ui_lock.release()

    def test_window_without_lock_behaves_as_before(self):
        win = FakeWindow(FakeControl(), with_lock=False)
        self.assertEqual(gui_guard.selpos(win, 100), 2)

    def test_same_thread_reentrance_does_not_deadlock(self):
        # Input-path code already inside a _ui_locked render tail calls
        # gui_guard again: the RLock must re-enter rather than report a
        # timeout-benign value.
        win = FakeWindow(FakeControl())
        with win._ui_lock:
            self.assertEqual(gui_guard.selpos(win, 100), 2)

    def test_guarded_call_vs_worker_mutation_cannot_interleave(self):
        # Simulate a worker holding the lock for a render tail while the
        # input thread reads: the read must wait or bail, never observe
        # a torn mid-mutation state.
        win = FakeWindow(FakeControl())
        worker_done = threading.Event()

        def worker():
            with win._ui_lock:
                worker_done.wait(0.3)

        t = threading.Thread(target=worker)
        t.start()
        # The worker holds the lock for ~300ms; the guarded read's 250ms
        # timeout fires first and returns the benign value.
        self.assertEqual(gui_guard.selpos(win, 100), -1)
        worker_done.set()
        t.join()
        # Afterwards the same read succeeds again.
        self.assertEqual(gui_guard.selpos(win, 100), 2)


if __name__ == '__main__':
    unittest.main()
