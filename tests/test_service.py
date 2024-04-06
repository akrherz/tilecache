"""Tests."""

import os

import mock
import pytest
from TileCache.Service import Service, wsgiHandler


@pytest.fixture
def service():
    """Return a service object."""
    # build a full path to the tilecache.cfg file found in this same directory
    cfg_fn = os.path.join(os.path.dirname(__file__), "tilecache.cfg")
    return Service.load(cfg_fn)


def test_generate_crossdomain_xml(service):
    """Exercise API."""
    assert service.generate_crossdomain_xml() is not None


def test_bad_xyz(service):
    """Test what happens when we send a bad loc."""
    env = {
        "QUERY_STRING": "",
        "PATH_INFO": "/1.0.0/usstates/7.333/32.33/49.33.png",
        "REQUEST_METHOD": "GET",
        "SCRIPT_NAME": "tile.py",
        "wsgi.input": mock.MagicMock(),
    }
    sr = mock.MagicMock()
    res = wsgiHandler(env, sr, service)
    assert res[0][:4] == b"An e"


def test_wsgi_handler(service):
    """Exercise API."""
    env = {
        "QUERY_STRING": "",
        "PATH_INFO": "/1.0.0/usstates/7/32/49.png",
        "REQUEST_METHOD": "GET",
        "SCRIPT_NAME": "tile.py",
        "wsgi.input": mock.MagicMock(),
    }
    sr = mock.MagicMock()
    res = wsgiHandler(env, sr, service)
    assert res[0][:4] == b"\x89PNG"
