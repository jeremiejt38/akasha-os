"""Akasha Remote — pure battery alert threshold logic.

No dependency on xbmc*/bluetoothctl, so this module can be unit tested with
plain `python3 -m unittest` (see docs/talos-strategy.md in the akasha-os
repo). `service.akasha.remote/service.py` adapts this to the real Kodi
notification API and the real Bluetooth battery reading.
"""

LOW_BATTERY_THRESHOLD = 15
# Hysteresis: once alerted, the battery must climb back above this before a
# second alert can fire -- otherwise a battery hovering right at the
# threshold (e.g. 14/15/14/15...) would spam a notification every poll.
RESET_THRESHOLD = 20


class BatteryAlertTracker:
    """Tracks whether a low-battery alert is currently "armed" (not yet
    fired since the battery last recovered above RESET_THRESHOLD)."""

    def __init__(self, low_threshold=LOW_BATTERY_THRESHOLD, reset_threshold=RESET_THRESHOLD):
        if reset_threshold <= low_threshold:
            raise ValueError('reset_threshold must be greater than low_threshold')
        self.low_threshold = low_threshold
        self.reset_threshold = reset_threshold
        self._alerted = False

    def observe(self, percent):
        """Feed a new battery percentage reading.

        Returns True exactly once per drop below `low_threshold` (i.e. the
        caller should show a notification), False otherwise. The alert
        re-arms once the battery climbs back above `reset_threshold`.
        """
        if percent is None:
            return False
        if percent >= self.reset_threshold:
            self._alerted = False
            return False
        if percent < self.low_threshold and not self._alerted:
            self._alerted = True
            return True
        return False
