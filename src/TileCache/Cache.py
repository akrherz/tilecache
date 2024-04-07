"""BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors"""

YESVALS = ["yes", "y", "t", "true"]


class Cache(object):
    """Base Cache"""

    def __init__(
        self,
        timeout=30.0,
        stale_interval=300.0,
        readonly=False,
        expire=False,
        sendfile=False,
        **kwargs,
    ):
        """Constructor"""
        self.stale = float(stale_interval)
        self.timeout = float(timeout)
        self.readonly = readonly
        self.expire = expire
        self.sendfile = sendfile and sendfile.lower() in YESVALS
        if expire is not False:
            self.expire = float(expire)

    def getKey(self, tile):
        raise NotImplementedError()

    def get(self, tile):
        raise NotImplementedError()

    def set(self, tile, data):
        raise NotImplementedError()
