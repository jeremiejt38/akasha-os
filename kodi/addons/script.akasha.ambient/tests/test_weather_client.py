import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import weather_client  # noqa: E402


def _fake_forecast_response(temperature=18, code=2):
    def fetch(url):
        return {'current': {'temperature_2m': temperature, 'weather_code': code}}
    return fetch


def _fake_geocoding_response(lat=45.75, lon=4.85):
    def fetch(url):
        return {'results': [{'latitude': lat, 'longitude': lon}]}
    return fetch


def _failing_fetch(url):
    raise OSError('network unreachable')


class ConditionLabelTests(unittest.TestCase):
    def test_known_code(self):
        self.assertEqual(weather_client.condition_label_for_code(0), 'Ciel degage')

    def test_unknown_code_returns_placeholder(self):
        self.assertEqual(weather_client.condition_label_for_code(12345), 'Inconnu')

    def test_non_numeric_code_returns_placeholder(self):
        self.assertEqual(weather_client.condition_label_for_code('nope'), 'Inconnu')


class GeocodeCityTests(unittest.TestCase):
    def test_resolves_known_city(self):
        result = weather_client.geocode_city(_fake_geocoding_response(), 'Lyon')
        self.assertEqual(result, (45.75, 4.85))

    def test_empty_city_returns_none(self):
        self.assertIsNone(weather_client.geocode_city(_fake_geocoding_response(), ''))

    def test_no_results_returns_none(self):
        self.assertIsNone(weather_client.geocode_city(lambda url: {'results': []}, 'Nowhereville'))

    def test_network_failure_returns_none(self):
        self.assertIsNone(weather_client.geocode_city(_failing_fetch, 'Lyon'))


class FetchCurrentWeatherTests(unittest.TestCase):
    def test_normalizes_response(self):
        result = weather_client.fetch_current_weather(_fake_forecast_response(18, 2), 48.85, 2.35)
        self.assertEqual(result['temperature'], 18)
        self.assertEqual(result['weather_code'], 2)
        self.assertEqual(result['condition_label'], 'Partiellement nuageux')
        self.assertIn('fetched_at', result)

    def test_network_failure_returns_none(self):
        self.assertIsNone(weather_client.fetch_current_weather(_failing_fetch, 48.85, 2.35))

    def test_malformed_response_returns_none(self):
        self.assertIsNone(
            weather_client.fetch_current_weather(lambda url: {'unexpected': True}, 48.85, 2.35)
        )


class CacheTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'sub', 'weather-cache.json')
            data = {'temperature': 18, 'fetched_at': 1000.0}
            self.assertTrue(weather_client.save_cache(cache_path, data))
            self.assertEqual(weather_client.load_cache(cache_path), data)

    def test_load_missing_file_returns_none(self):
        self.assertIsNone(weather_client.load_cache('/nonexistent/path/cache.json'))

    def test_load_corrupted_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'cache.json')
            with open(cache_path, 'w') as f:
                f.write('{not valid json')
            self.assertIsNone(weather_client.load_cache(cache_path))

    def test_is_cache_fresh(self):
        self.assertTrue(weather_client.is_cache_fresh({'fetched_at': 1000}, now=1000 + 60, max_age_seconds=3600))
        self.assertFalse(weather_client.is_cache_fresh({'fetched_at': 1000}, now=1000 + 4000, max_age_seconds=3600))
        self.assertFalse(weather_client.is_cache_fresh(None, now=1000))
        self.assertFalse(weather_client.is_cache_fresh({}, now=1000))


class GetWeatherTests(unittest.TestCase):
    def test_uses_fresh_cache_without_fetching(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'cache.json')
            weather_client.save_cache(cache_path, {'temperature': 10, 'fetched_at': 1000.0})

            calls = []

            def fetch(url):
                calls.append(url)
                raise AssertionError('should not fetch when cache is fresh')

            result = weather_client.get_weather(fetch, cache_path, 48.85, 2.35, now=1000 + 60)
            self.assertEqual(result['temperature'], 10)
            self.assertEqual(calls, [])

    def test_fetches_and_caches_when_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'cache.json')
            weather_client.save_cache(cache_path, {'temperature': 10, 'fetched_at': 0.0})

            result = weather_client.get_weather(
                _fake_forecast_response(21, 0), cache_path, 48.85, 2.35, now=100000,
            )
            self.assertEqual(result['temperature'], 21)
            # The fresh reading must have been persisted for next time.
            self.assertEqual(weather_client.load_cache(cache_path)['temperature'], 21)

    def test_falls_back_to_stale_cache_on_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'cache.json')
            weather_client.save_cache(cache_path, {'temperature': 10, 'fetched_at': 0.0})

            result = weather_client.get_weather(_failing_fetch, cache_path, 48.85, 2.35, now=100000)
            self.assertEqual(result['temperature'], 10)

    def test_returns_none_when_no_cache_and_network_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, 'cache.json')
            result = weather_client.get_weather(_failing_fetch, cache_path, 48.85, 2.35, now=100000)
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
