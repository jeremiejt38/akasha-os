"""Unit tests for timeline_reporter.py (B3 `/:/timeline` reports).

Same stub pattern as test_up_next.py: xbmc/xbmcgui are replaced before
import, Window(10000) is dict-backed, the PlexClient is a MagicMock.
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        mock = MagicMock(name=name)
        setattr(self, name, mock)
        return mock


class FakeHomeWindow:
    """Dict-backed stand-in for xbmcgui.Window(10000)."""

    def __init__(self):
        self._props = {}

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')


_home = FakeHomeWindow()

xbmc = _StubModule('xbmc')
xbmcaddon = _StubModule('xbmcaddon')
xbmcaddon.Addon = MagicMock
xbmcgui = _StubModule('xbmcgui')
xbmcgui.Window = lambda *args: _home

sys.modules.setdefault('xbmc', xbmc)
sys.modules.setdefault('xbmcaddon', xbmcaddon)
sys.modules.setdefault('xbmcgui', xbmcgui)
sys.modules.setdefault('xbmcvfs', _StubModule('xbmcvfs'))

import osd_menu  # noqa: E402
import plex_client  # noqa: E402
import timeline_reporter  # noqa: E402

# Pin the pieces timeline_reporter dereferences so the tests are
# independent of whichever stub module earlier tests installed.
timeline_reporter._home = lambda: _home
_fake_player = MagicMock()
timeline_reporter.xbmc.Player = lambda *args: _fake_player


def _reporter(server='http://srv', token='tk', rating_key='42'):
    factory = MagicMock()
    client = factory.return_value
    rep = timeline_reporter.TimelineReporter(
        context_provider=lambda: (server, token, rating_key, '/part/42'),
        client_factory=lambda s, t: client)
    return rep, client


def _pin_stubs():
    """Re-pin the shared stub attributes other test files overwrite.

    The xbmc stub module object is shared across the whole pytest run:
    test_up_next reassigns xbmc.Player/getCondVisibility on it at import
    time, so pinning once here is not enough -- it must happen per test.
    """
    timeline_reporter._home = lambda: _home
    timeline_reporter.xbmc.Player = lambda *args: _fake_player
    timeline_reporter.xbmc.getCondVisibility = lambda cond: False
    timeline_reporter.xbmc.log = MagicMock()


class TickTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _pin_stubs()
        # side_effect=... matters: reset_mock() alone does NOT clear a
        # side_effect left by an earlier (alphabetical) test.
        _fake_player.reset_mock(return_value=True, side_effect=True)
        _fake_player.isPlayingVideo.return_value = True
        _fake_player.getTime.return_value = 61.0
        _fake_player.getTotalTime.return_value = 2520.0

    def test_reports_playing_position_in_ms(self):
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_called_once_with(
            '42', 61000, 2520000, 'playing', session=rep._session)

    def test_reports_paused_state(self):
        timeline_reporter.xbmc.getCondVisibility = lambda cond: True
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_called_once_with(
            '42', 61000, 2520000, 'paused', session=rep._session)

    def test_no_report_without_context(self):
        rep, client = _reporter(server='', token='', rating_key='')
        rep.tick()
        client.report_timeline.assert_not_called()

    def test_no_report_when_not_playing(self):
        _fake_player.isPlayingVideo.return_value = False
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_not_called()

    def test_no_report_when_duration_unknown(self):
        _fake_player.getTotalTime.return_value = 0
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_not_called()

    def test_player_runtime_error_is_swallowed(self):
        _fake_player.isPlayingVideo.side_effect = RuntimeError
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_not_called()

    def test_quality_switch_suppresses_report(self):
        _home.setProperty(osd_menu.PROP_SWITCHING, '1')
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.assert_not_called()

    def test_api_error_is_swallowed_and_logged_once(self):
        rep, client = _reporter()
        client.report_timeline.side_effect = plex_client.PlexAPIError('down')
        rep.tick()
        rep.tick()
        self.assertEqual(rep._failures, 2)
        timeline_reporter.xbmc.log.assert_called_once()

    def test_recovery_resets_failure_count(self):
        rep, client = _reporter()
        client.report_timeline.side_effect = plex_client.PlexAPIError('x')
        rep.tick()
        client.report_timeline.side_effect = None
        rep.tick()
        self.assertEqual(rep._failures, 0)


class FinishTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _pin_stubs()
        _fake_player.reset_mock(return_value=True, side_effect=True)
        _fake_player.isPlayingVideo.return_value = True
        _fake_player.getTime.return_value = 61.0
        _fake_player.getTotalTime.return_value = 2520.0

    def test_finish_reports_stopped_with_last_position(self):
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.reset_mock()
        rep.finish()
        client.report_timeline.assert_called_once_with(
            '42', 61000, 2520000, 'stopped', session=rep._session)
        self.assertTrue(rep._stop_event.is_set())

    def test_finish_without_playback_reports_nothing(self):
        rep, client = _reporter()
        rep.finish()
        client.report_timeline.assert_not_called()

    def test_finish_position_override_beats_stale_tick(self):
        rep, client = _reporter()
        rep.tick()  # _last time = 61000
        rep.finish(position_ms=734000)
        self.assertEqual(
            client.report_timeline.call_args_list[-1].args,
            ('42', 734000, 2520000, 'stopped'))
        self.assertEqual(
            client.report_timeline.call_args_list[-1].kwargs['session'],
            rep._session)


class StoppedTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _pin_stubs()
        _fake_player.reset_mock(return_value=True, side_effect=True)
        _fake_player.isPlayingVideo.return_value = True
        _fake_player.getTime.return_value = 61.0
        _fake_player.getTotalTime.return_value = 2520.0

    def test_stopped_reports_immediately_and_clears_last(self):
        rep, client = _reporter()
        rep.tick()
        client.report_timeline.reset_mock()
        rep.stopped(position_ms=62000)
        client.report_timeline.assert_called_once_with(
            '42', 62000, 2520000, 'stopped', session=rep._session)
        # Once reported, the item is done -- finish() must not repeat it.
        rep.finish()
        self.assertEqual(client.report_timeline.call_count, 1)

    def test_stopped_without_playback_is_noop(self):
        rep, client = _reporter()
        rep.stopped(position_ms=62000)
        client.report_timeline.assert_not_called()


class RunTests(unittest.TestCase):

    def setUp(self):
        _home._props.clear()
        _pin_stubs()
        _fake_player.reset_mock(return_value=True, side_effect=True)
        _fake_player.isPlayingVideo.return_value = True
        _fake_player.getTime.return_value = 61.0
        _fake_player.getTotalTime.return_value = 2520.0

    def test_run_ticks_once_before_first_interval(self):
        # Plex reports at play start, not after REPORT_INTERVAL_SECONDS:
        # sub-interval plays still land a viewOffset for the stop report.
        rep, client = _reporter()
        rep._stop_event.set()
        rep.run()
        client.report_timeline.assert_called_once_with(
            '42', 61000, 2520000, 'playing', session=rep._session)

    def test_short_play_still_sends_stopped_report(self):
        rep, client = _reporter()
        rep._stop_event.set()
        rep.run()
        rep.finish()
        self.assertEqual(
            client.report_timeline.call_args_list[-1].args,
            ('42', 61000, 2520000, 'stopped'))


if __name__ == '__main__':
    unittest.main()
