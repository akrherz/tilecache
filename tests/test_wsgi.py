"""Run some WSGI tests via wuerkzeug."""

import os

import pytest
from werkzeug.test import Client

from TileCache import InvalidTMSRequest
from TileCache.Service import Service, wsgiHandler


@pytest.fixture
def client():
    """Return a service object."""

    def app(environ, start_response):
        # build a full path to the tilecache.cfg file found in this directory
        cfg_fn = os.path.join(os.path.dirname(__file__), "tilecache.cfg")
        return wsgiHandler(environ, start_response, Service.load(cfg_fn))

    return Client(app)


def test_250314_malformed_mrms(client):
    """Test the processing of mrms request without details."""
    res = client.get("/1.0.0/mrms/4/4/8.png")
    assert res.status_code == 404


def test_250314_malformed(client):
    """Test handling of another malformed request."""
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/profit2015/10/279/429.png/tile/10/429/279")
