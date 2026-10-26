"""B15 stream continuity: capture/persist/re-apply audio+subtitle prefs."""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'resources', 'lib'))

import test_aura_detail  # noqa: F401,E402 -- installs the fake xbmc modules

import stream_prefs  # noqa: E402


class _Addon:
    def __init__(self, settings=None):
        self.settings = dict(settings or {})

    def getSetting(self, key):
        return self.settings.get(key, '')

    def setSetting(self, key, value):
        self.settings[key] = value


class _Props:
    """JSON-RPC answer bank keyed by Player.GetProperties result."""
    def __init__(self, props):
        self.props = props
        self.calls = []


def _rpc_factory(props, calls):
    def fake(payload):
        req = json.loads(payload)
        calls.append(req)
        method = req['method']
        if method == 'Player.GetProperties':
            return json.dumps({'jsonrpc': '2.0', 'id': 1,
                               'result': props})
        return json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': {}})
    return fake


PROPS = {
    'audiostreams': [
        {'index': 0, 'language': 'eng', 'name': 'AAC'},
        {'index': 1, 'language': 'fra', 'name': 'Commentary'},
        {'index': 2, 'language': 'fra', 'name': 'AC3'},
    ],
    'currentaudiostream': {'index': 0, 'language': 'eng', 'name': 'AAC'},
    'subtitles': [
        {'index': 0, 'language': 'fra', 'name': 'Forced'},
        {'index': 1, 'language': 'eng', 'name': 'SDH'},
    ],
    'currentsubtitle': {'index': 0, 'language': 'fra', 'name': 'Forced'},
    'subtitleenabled': True,
}


class StreamPrefsTests(unittest.TestCase):

    def setUp(self):
        from unittest.mock import MagicMock
        # Which xbmc stub is in place depends on test order -- pin the
        # attribute so patch.object finds it regardless.
        stream_prefs.xbmc.executeJSONRPC = MagicMock()

    def _patch_props(self, props):
        calls = []
        return calls, patch.object(
            stream_prefs.xbmc, 'executeJSONRPC',
            side_effect=_rpc_factory(props, calls))

    def test_capture_selection(self):
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            sel = stream_prefs.capture_selection()
        self.assertEqual(sel['audio']['index'], 0)
        self.assertEqual(sel['audio']['language'], 'eng')
        self.assertEqual(sel['sub']['language'], 'fra')
        self.assertTrue(sel['sub_enabled'])

    def test_capture_none_without_audio(self):
        calls, rpc = self._patch_props({})
        with rpc:
            self.assertIsNone(stream_prefs.capture_selection())

    def test_persist_keyed_by_grandparent(self):
        addon = _Addon()
        item = {'rating_key': '10', 'grandparent_rating_key': '5'}
        stream_prefs.persist_selection(
            addon, item, {'audio': {'index': 1, 'language': 'fra'},
                          'sub': {}, 'sub_enabled': False})
        self.assertIn('stream.pref.5', addon.settings)

    def test_persist_falls_back_to_rating_key(self):
        addon = _Addon()
        stream_prefs.persist_selection(
            addon, {'rating_key': '77'},
            {'audio': {'index': 0, 'language': 'eng'},
             'sub': {}, 'sub_enabled': False})
        self.assertIn('stream.pref.77', addon.settings)

    def test_persist_ignores_empty_item(self):
        addon = _Addon()
        stream_prefs.persist_selection(
            addon, {}, {'audio': {'index': 0}})
        self.assertFalse(addon.settings)

    def test_apply_switches_audio_by_language(self):
        addon = _Addon({'stream.pref.5': json.dumps({
            'audio': {'index': 0, 'language': 'fra', 'name': 'AC3'},
            'sub': {}, 'sub_enabled': True})})
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            changed = stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '5'})
        self.assertTrue(changed)
        audio_calls = [c for c in calls
                       if c['method'] == 'Player.SetAudioStream']
        self.assertEqual(audio_calls[0]['params']['stream'], 2)

    def test_apply_prefers_exact_name_match(self):
        addon = _Addon({'stream.pref.5': json.dumps({
            'audio': {'index': 0, 'language': 'fra',
                      'name': 'Commentary'},
            'sub': {}, 'sub_enabled': False})})
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '5'})
        audio_calls = [c for c in calls
                       if c['method'] == 'Player.SetAudioStream']
        self.assertEqual(audio_calls[0]['params']['stream'], 1)

    def test_apply_disables_subtitles_when_saved_off(self):
        addon = _Addon({'stream.pref.5': json.dumps({
            'audio': {'index': 0, 'language': 'eng', 'name': 'AAC'},
            'sub': {}, 'sub_enabled': False})})
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '5'})
        sub_calls = [c for c in calls
                     if c['method'] == 'Player.SetSubtitle']
        self.assertEqual(sub_calls[0]['params']['subtitle'], 'off')
        self.assertFalse(sub_calls[0]['params']['enable'])

    def test_apply_no_saved_pref_no_calls(self):
        addon = _Addon()
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            changed = stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '9'})
        self.assertFalse(changed)
        setters = [c for c in calls if c['method'] != 'Player.GetProperties']
        self.assertFalse(setters)

    def test_apply_same_stream_no_switch(self):
        addon = _Addon({'stream.pref.5': json.dumps({
            'audio': {'index': 0, 'language': 'eng', 'name': 'AAC'},
            'sub': {'index': 0, 'language': 'fra', 'name': 'Forced'},
            'sub_enabled': True})})
        calls, rpc = self._patch_props(PROPS)
        with rpc:
            changed = stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '5'})
        self.assertFalse(changed)

    def test_apply_missing_language_keeps_default(self):
        addon = _Addon({'stream.pref.5': json.dumps({
            'audio': {'index': 0, 'language': 'jpn', 'name': 'AAC'},
            'sub': {}, 'sub_enabled': False})})
        calls, rpc = self._patch_props(dict(
            PROPS, currentsubtitle={'index': 0}))
        with rpc:
            stream_prefs.apply_saved_streams(
                addon, {'grandparent_rating_key': '5'})
        audio_calls = [c for c in calls
                       if c['method'] == 'Player.SetAudioStream']
        self.assertFalse(audio_calls)

    def _patch_home(self, props):
        from unittest.mock import MagicMock
        win = MagicMock()
        win.getProperty.side_effect = lambda k: props.get(k, '')
        return patch.object(stream_prefs, '_home', return_value=win)

    def test_current_item_reads_prop(self):
        with self._patch_home({stream_prefs.PROP_ITEM:
                               json.dumps({'rating_key': '42'})}):
            self.assertEqual(
                stream_prefs.current_item()['rating_key'], '42')

    def test_current_item_empty(self):
        with self._patch_home({}):
            self.assertEqual(stream_prefs.current_item(), {})

    def test_current_item_malformed_json(self):
        with self._patch_home({stream_prefs.PROP_ITEM: '{nope'}):
            self.assertEqual(stream_prefs.current_item(), {})


if __name__ == '__main__':
    unittest.main()
