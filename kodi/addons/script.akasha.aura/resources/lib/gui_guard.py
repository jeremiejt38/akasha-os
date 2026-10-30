#!/usr/bin/env python3
"""Guarded accessors for Kodi GUI controls.

Two Kodi crash/exception classes motivated this module (kodi_crashlog
2026-10-29): a native SEGV inside ControlList::getSelectedPosition() when a
pending Python callback ran against a control whose window was mid-teardown,
and the recurring 'EXCEPTION: Non-Existent Control' log spam whenever
getControl() probes an id the XML does not declare.

Python cannot make a dead native control safe to touch, but it can avoid
the two dominant trigger patterns:

- calling selection/focus methods on an EMPTY Python-fed list (Kodi logs a
  focus failure, and selection calls on zero-item lists read a stale
  m_iSelect boundary);
- calling getControl() for ids that may not exist, which logs an
  EXCEPTION line even when the RuntimeError is caught.

Every helper degrades to a benign value (-1 / None / False) instead of
raising.
"""
import xbmcgui  # noqa: F401  (kept for the Kodi runtime contract)

_LOCK_TIMEOUT_SECONDS = 0.25


def _acquire(window):
    """Take the window's UI lock for the duration of one guarded call.

    Selection reads race worker-side list rebuilds (the SEGV signature in
    the crash logs): a getSelectedPosition() landing between a worker's
    reset() and addItems() reads a dead boundary. Windows that expose a
    `_ui_lock` (RLock shared with their render path) are serialized here;
    a held lock times out rather than blocking input -- the caller gets
    its benign value and the user keeps control.

    Returns the acquired lock, ``False`` on timeout, or ``None`` when the
    window carries no lock.
    """
    lock = getattr(window, '_ui_lock', None)
    if lock is None or not hasattr(lock, 'acquire'):
        return None
    return lock if lock.acquire(timeout=_LOCK_TIMEOUT_SECONDS) else False


def selpos(window, control_id):
    """getSelectedPosition() guarded: -1 when the control is missing,
    empty, the window is being torn down, or the UI lock is busy."""
    lock = _acquire(window)
    if lock is False:
        return -1
    try:
        try:
            return pos(window.getControl(control_id))
        except RuntimeError:
            return -1
    finally:
        if lock is not None:
            lock.release()


def _empty(control):
    """True when the control provably holds zero items. size() returning
    None or a non-int (test stubs, non-list controls) counts as
    'unknown', not empty."""
    try:
        size = control.size()
        return isinstance(size, int) and size <= 0
    except (RuntimeError, AttributeError, TypeError):
        return False


def pos(control):
    """getSelectedPosition() on an already-fetched control."""
    try:
        if control is None or _empty(control):
            return -1
        return control.getSelectedPosition()
    except (RuntimeError, AttributeError):
        return -1


def selitem(window, control_id):
    """getSelectedItem() guarded: None on missing/empty/dead control or
    a busy UI lock."""
    lock = _acquire(window)
    if lock is False:
        return None
    try:
        try:
            c = window.getControl(control_id)
            if c is None or _empty(c):
                return None
            return c.getSelectedItem()
        except (RuntimeError, AttributeError):
            return None
    finally:
        if lock is not None:
            lock.release()


def focus(window, control_id):
    """setFocus() only when the control exists AND (for list controls)
    holds at least one item -- focusing an empty Python-fed list logs a
    focus failure and leaves the dialog without a selection target.
    Returns True when focus was actually moved."""
    lock = _acquire(window)
    if lock is False:
        return False
    try:
        try:
            c = window.getControl(control_id)
        except RuntimeError:
            return False
        try:
            if _empty(c):
                return False
            window.setFocus(c)
            return True
        except RuntimeError:
            return False
    finally:
        if lock is not None:
            lock.release()


def select(window, control_id, position):
    """selectItem() guarded by existence + bounds. Returns True on
    success."""
    lock = _acquire(window)
    if lock is False:
        return False
    try:
        try:
            c = window.getControl(control_id)
            if c is None:
                return False
            size = c.size()
            if position < 0:
                return False
            if isinstance(size, int) and position >= size:
                return False
            c.selectItem(position)
            return True
        except (RuntimeError, AttributeError):
            return False
    finally:
        if lock is not None:
            lock.release()
