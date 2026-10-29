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


def selpos(window, control_id):
    """getSelectedPosition() guarded: -1 when the control is missing,
    empty, or the window is being torn down."""
    try:
        return pos(window.getControl(control_id))
    except RuntimeError:
        return -1


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
    """getSelectedItem() guarded: None on missing/empty/dead control."""
    try:
        c = window.getControl(control_id)
        if c is None or _empty(c):
            return None
        return c.getSelectedItem()
    except (RuntimeError, AttributeError):
        return None


def focus(window, control_id):
    """setFocus() only when the control exists AND (for list controls)
    holds at least one item -- focusing an empty Python-fed list logs a
    focus failure and leaves the dialog without a selection target.
    Returns True when focus was actually moved."""
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


def select(window, control_id, position):
    """selectItem() guarded by existence + bounds. Returns True on
    success."""
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
