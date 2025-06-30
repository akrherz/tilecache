"""Memcached Caching Provider
BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors
"""

# Important to use a thread-safe pool as mod_wsgi is running this in threads
from pymemcache.client.hash import HashClient
from six import string_types

from TileCache.Cache import Cache


class Memcached(Cache):
    """Implements a cache"""

    def __init__(self, servers="127.0.0.1:11211", **kwargs):
        """Constructor"""
        Cache.__init__(self, **kwargs)
        if isinstance(servers, string_types):
            servers = [s.strip() for s in servers.split(",")]
        self.cache = HashClient(servers, use_pooling=True)
        self.timeout = int(kwargs.get("timeout", 0))

    def getKey(self, tile):
        """Get the key for this tile"""
        return "/".join(map(str, [tile.layer.name, tile.x, tile.y, tile.z]))

    def get(self, tile):
        """Get the cache data"""
        key = self.getKey(tile)
        try:
            tile.data = self.cache.get(key)
        except Exception:
            # Yes, we are silently ignoring errors here.
            tile.data = None
        return tile.data

    def set(self, tile, data):
        """Set the cache data"""
        if self.readonly:
            return data
        key = self.getKey(tile)
        self.cache.set(key, data, self.timeout)
        return data
