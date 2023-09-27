"""Tests."""
import os

import pytest
from TileCache.Service import Service


@pytest.fixture
def service():
    """Return a service object."""
    # build a full path to the tilecache.cfg file found in this same directory
    cfg_fn = os.path.join(os.path.dirname(__file__), "tilecache.cfg")
    return Service.load(cfg_fn)


def test_generate_crossdomain_xml(service):
    """Exercise API."""
    assert service.generate_crossdomain_xml() is not None
