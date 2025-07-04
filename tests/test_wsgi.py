"""Run some WSGI tests via wuerkzeug."""

import os

import pytest
from pytest_httpx import HTTPXMock
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


def test_index_error_invalid_zoom(client):
    """Test the error when we request too high a zoom value."""
    res = client.get("/1.0.0/profit2015/109/279/429.png")
    assert res.status_code == 422


def test_wms_500s(httpx_mock: HTTPXMock, client):
    """Test what happens when two WMS requests fail."""
    httpx_mock.add_response(status_code=404)
    httpx_mock.add_response(status_code=404)
    res = client.get("/1.0.0/profit2015/10/279/429.png")
    assert res.status_code == 503


def test_wms_failure(httpx_mock: HTTPXMock, client):
    """Test a backend WMS Failure."""
    httpx_mock.add_response(status_code=200, content=b"..IReadBlock failed at")
    httpx_mock.add_response(status_code=200, content=b"..IReadBlock failed at")
    res = client.get("/1.0.0/profit2015/10/279/429.png")
    assert res.status_code == 503


def test_250325_bad_ridge(client):
    """Test an incomplete ridge request."""
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/ridge::N0Q/4/4/8.png")


def test_250320_hrrr(client):
    """Test a HRRR request that has no backend layer defined."""
    res = client.get("/1.0.0/hrrr::REFD-F0720-2025032000/4/4/8.png")
    assert res.status_code == 404


def test_250326_space_in_request(client):
    """Test that a space in the request is handled correctly."""
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/ridge::USCOMP-N0R-202502234:0%20/5/7/11.png")


def test_valid_ridge_t_request(client):
    """Test something that should work."""
    res = client.get("/1.0.0/ridge::USCOMP-N0R-202502232330/5/7/11.png")
    assert res.status_code == 200


def test_250319_float_zoom(client):
    """Unsure if this is valid or not, but alas."""
    res = client.get("/1.0.0/c-900913/4.9/4/8.png")
    assert res.status_code == 200


def test_250319_badint(client):
    """Test the handling of a bad integer."""
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/profit2015/10/a/429.png")
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/profit2015/10/10/a.png")


def test_250529_malformed_mrms_v2(client):
    """Test the processing of a malformed mrms request."""
    res = client.get("mrms::CAPE/8/62/101.png")
    assert res.status_code == 404


def test_250314_malformed_mrms(client):
    """Test the processing of mrms request without details."""
    res = client.get("/1.0.0/mrms/4/4/8.png")
    assert res.status_code == 404


def test_250314_malformed(client):
    """Test handling of another malformed request."""
    with pytest.raises(InvalidTMSRequest):
        client.get("/1.0.0/profit2015/10/279/429.png/tile/10/429/279")
