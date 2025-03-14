#!/usr/bin/env python

# BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
import time
from typing import Optional

import httpx

from TileCache import BackendWMSFailure

# setting this to True will exchange more useful error messages
# for privacy, hiding URLs and error messages.
HIDE_ALL = False


class WMS(object):
    fields = ("bbox", "srs", "width", "height", "format", "layers", "styles")
    defaultParams = {"version": "1.1.1", "request": "GetMap", "service": "WMS"}
    __slots__ = ("base", "params", "client", "data", "response")

    def __init__(self, base, params, user=None, password=None):
        """Constructor"""
        self.base = base
        if self.base[-1] not in "?&":
            if "?" in self.base:
                self.base += "&"
            else:
                self.base += "?"

        self.params = {}

        for key, val in self.defaultParams.items():
            if self.base.lower().rfind("%s=" % key.lower()) == -1:
                self.params[key] = val
        for key in self.fields:
            if key in params:
                self.params[key] = params[key]
            elif self.base.lower().rfind("%s=" % key.lower()) == -1:
                self.params[key] = ""

    def url(self):
        """Generate URL"""
        return self.base + urlencode(self.params)

    def fetch(self) -> Optional[bytes]:
        """Fetch image from backend"""
        data = None
        for attempt in range(1, 3):
            try:
                resp = httpx.get(self.url(), timeout=20)
                # Error if we don't get a 200
                resp.raise_for_status()
                # Error if we don't get an image back
                if resp.headers.get("content-type") != "image/png":
                    # Account for an edge case of Mapserver failing due to
                    # file getting replaced underneath its cached reference
                    if (
                        attempt == 1
                        and resp.text.find("IReadBlock failed at") > -1
                    ):
                        time.sleep(1)
                        continue
                    msg = (
                        "Did not get image data back. \n"
                        f"URL: {self.url()}\nStatus: {resp.status_code}\n"
                        f"Response: \n{resp.text}"
                    )
                    raise BackendWMSFailure(msg)
                data = resp.content
                break
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise BackendWMSFailure("WMS image failure") from exc
        return data

    def setBBox(self, box):
        """set bounding box"""
        self.params["bbox"] = ",".join(map(str, box))
