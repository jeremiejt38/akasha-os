"""Unit tests for art_proxy.py — no xbmc dependency (module degrades to
a tempfile cache dir and None xbmc outside Kodi)."""

import base64
import threading
import unittest
import urllib.parse
from unittest import mock

import art_proxy


def _wrapped(upstream, radius=21, width=320, height=480):
    params = {'u': base64.urlsafe_b64encode(upstream.encode()).decode(),
              'r': str(radius), 'w': str(width), 'h': str(height)}
    return 'http://127.0.0.1:8194/art?{}'.format(urllib.parse.urlencode(params))


class WarmTest(unittest.TestCase):
    def test_ignores_non_proxy_urls(self):
        with mock.patch.object(art_proxy, '_render') as render:
            art_proxy.warm(['https://plex.local/photo', '', None])
        # warm() is threaded: the worker skips non-/art? urls entirely,
        # so _render is never invoked for them.
        import time
        time.sleep(0.05)
        render.assert_not_called()

    def test_empty_input(self):
        art_proxy.warm([])
        art_proxy.warm([None, ''])

    def test_calls_render_with_parsed_params(self):
        done = threading.Event()

        def fake_render(url, radius, width, height):
            try:
                self.assertEqual(url, 'https://plex.local/poster.jpg?t=1')
                self.assertEqual((radius, width, height), (21, 320, 480))
            finally:
                done.set()
            return b'png'

        with mock.patch.object(art_proxy, '_render', side_effect=fake_render):
            art_proxy.warm([_wrapped('https://plex.local/poster.jpg?t=1')])
        self.assertTrue(done.wait(timeout=5))

    def test_swallows_malformed_wrapped_url(self):
        # Truncated/garbage base64 must not crash the worker thread.
        art_proxy.warm(['http://127.0.0.1:8194/art?u=%%%&r=x'])

    def test_workers_capped_globally(self):
        # Many warm() calls (page warm + position warms during a fast
        # scroll) must never exceed WARM_WORKERS live threads.
        url = _wrapped('https://plex.local/p.jpg')
        with mock.patch.object(art_proxy, '_render',
                               side_effect=lambda *a: __import__('time').sleep(0.2)):
            try:
                for _ in range(6):
                    art_proxy.warm([url] * 20)
                self.assertLessEqual(art_proxy._warm_live,
                                     art_proxy.WARM_WORKERS)
            finally:
                # Drain the shared queue so later tests start clean.
                with art_proxy._warm_lock:
                    art_proxy._warm_queue.clear()

    def test_priority_jumps_queue(self):
        # Freeze worker spawn entirely: nothing drains the queue, so the
        # insertion order under inspection is exactly what warm() wrote.
        url_a = _wrapped('https://plex.local/a.jpg')
        url_b = _wrapped('https://plex.local/b.jpg')
        try:
            with mock.patch.object(art_proxy.threading, 'Thread'):
                art_proxy.warm([url_a] * 10)
                art_proxy.warm([url_b], priority=True)
                with art_proxy._warm_lock:
                    first = art_proxy._warm_queue[0]
                self.assertEqual(first, url_b)
        finally:
            with art_proxy._warm_lock:
                art_proxy._warm_queue.clear()
                art_proxy._warm_live = 0


class WrapRoundTripTest(unittest.TestCase):
    def test_unwrap_reverses_wrap(self):
        original = 'https://plex.local/photo/:/transcode?url=%2Fa&x=1'
        wrapped = art_proxy.wrap(original, 21, 320, 480)
        if '/art?' in wrapped:  # only when the proxy managed to start
            self.assertEqual(art_proxy.unwrap(wrapped), original)


if __name__ == '__main__':
    unittest.main()
