#!/usr/bin/env python3
"""Plex `/:/timeline` progress reporter (parity backlog B3).

While Aura's playback supervision loop runs in default.py, this daemon
thread reports the playback position to the server every
REPORT_INTERVAL_SECONDS -- same cadence as the official Plex clients.
Without it the server never learns a partial viewOffset: an interrupted
movie would not show a resume point on another device, and "Continue
Watching" would go stale mid-session.

Context (which server, token and ratingKey back the currently playing
file) is read from the Window(10000) properties Aura persists at play
time, exactly like the OSD menus do -- so externally started playback
(PM4K, JSON-RPC) simply reports nothing, as no mapping exists for it.
"""
import threading
import uuid

import xbmc
import xbmcgui

import osd_menu
import plex_client

# Official clients report every 5-10s; 10s keeps the Pi4's network and
# the server log quiet while viewOffset drifts at most ~0.4% per report
# on a 42-min episode.
REPORT_INTERVAL_SECONDS = 10.0


def _home():
    return xbmcgui.Window(10000)


class TimelineReporter(threading.Thread):
    """Daemon pinging `/:/timeline` while a video plays.

    `context_provider` / `client_factory` are injectable for tests; in
    production they resolve the playing item's (server, token, ratingKey)
    from the persisted playback context and build a real PlexClient.
    """

    def __init__(self, context_provider=None, client_factory=None):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self._context_provider = context_provider or osd_menu._playback_context
        self._client_factory = client_factory or plex_client.PlexClient
        # Plex only persists viewOffset for reports tied to a session id;
        # one UUID per playback session (Up Next chains keep it).
        self._session = str(uuid.uuid4())
        # Last confirmed playing snapshot, reused for the final
        # state=stopped report after playback actually ends.
        self._last = None
        self._failures = 0

    def tick(self):
        """One reporting round -- no-op unless a mapped item is playing."""
        # A quality switch stop/starts the player inside Aura; reporting
        # during that gap would send a bogus position for the old item.
        if _home().getProperty(osd_menu.PROP_SWITCHING):
            return
        server, token, rating_key, _part_key = self._context_provider()
        if not server or not token or not rating_key:
            return
        player = xbmc.Player()
        try:
            if not player.isPlayingVideo():
                return
            time_ms = int(player.getTime() * 1000)
            duration_ms = int(player.getTotalTime() * 1000)
        except RuntimeError:
            return
        if not duration_ms:
            return
        state = ('paused' if xbmc.getCondVisibility('Player.Paused')
                 else 'playing')
        self._last = (server, token, rating_key, time_ms, duration_ms)
        self._report(state)

    def stopped(self, position_ms=None):
        """Immediate `state=stopped` for the item that just ended.

        Plex clients send it when playback stops, not when the app
        exits -- Aura's supervision loop calls _run_window() (blocking
        doModal) after each play, so without this the server keeps the
        session 'playing' until the user eventually quits Aura. The
        thread keeps running: an Up Next chain may start a new item."""
        if self._last is None:
            return
        if position_ms is not None:
            server, token, rk, _t, dur = self._last
            self._last = (server, token, rk, int(position_ms), dur)
        self._report('stopped')
        self._last = None

    def finish(self, position_ms=None):
        """Final `stopped` report, then terminate the thread loop.

        `position_ms` overrides the last tick's time -- the supervision
        loop polls the player every 500ms while the reporter only ticks
        every 10s, so the stop position it sees is fresher."""
        if self._last:
            if position_ms is not None:
                server, token, rk, _t, dur = self._last
                self._last = (server, token, rk, int(position_ms), dur)
            self._report('stopped')
        self._stop_event.set()

    def run(self):
        # First report immediately, like Plex's own clients: a play that
        # ends inside the first interval still lands a viewOffset, and
        # the item shows in Now Playing / On Deck straight away.
        try:
            self.tick()
        except Exception:
            pass
        while not self._stop_event.wait(REPORT_INTERVAL_SECONDS):
            try:
                self.tick()
            except Exception:
                pass

    def _report(self, state):
        server, token, rating_key, time_ms, duration_ms = self._last
        try:
            self._client_factory(server, token).report_timeline(
                rating_key, time_ms, duration_ms, state,
                session=self._session)
            self._failures = 0
        except plex_client.PlexAPIError as e:
            # Offline servers are common on the LAN (Plex down, VPN cut);
            # log the first failure of a burst, then stay quiet.
            self._failures += 1
            if self._failures == 1:
                xbmc.log('Akasha Aura: timeline report failed: {}'.format(e),
                         xbmc.LOGWARNING)
