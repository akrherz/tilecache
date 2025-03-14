"""BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors"""


class BackendWMSFailure(Exception):
    """Raised when the backend WMS fails."""


class InvalidTMSRequest(Exception):
    """Raised when a TMS request is invalid."""
