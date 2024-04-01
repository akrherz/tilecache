"""Test Memcached."""

from TileCache.Caches.Memcached import Memcached


def test_api():
    """Can we import?"""
    c = Memcached()
    assert c.cache.get("blah") is None
