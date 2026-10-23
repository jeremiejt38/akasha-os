"""Shared test fixtures for the Aura test suite."""

import pytest


@pytest.fixture(autouse=True)
def _clear_http_layer_state():
    """plex_client and connector_client keep module-level read caches and
    offline-breaker state; without a reset a previous test's mocked
    response leaks into the next test's expectations."""
    import connector_client
    import plex_client

    for module in (connector_client, plex_client):
        module._read_cache.clear()
        module._offline_until.clear()
    yield
