"""BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors"""

import configparser
import email
import os
import sys
import time
import traceback

from paste.request import parse_formvars
from six import string_types

import TileCache.Cache as Cache
import TileCache.Layer as Layer
from TileCache import (
    BackendWMSFailure,
    InvalidTMSRequest,
    OutOfBoundsZoomLevel,
)
from TileCache.base import (
    MalformedRequestException,
    TileCacheException,
    TileCacheFutureException,
    TileCacheLayerNotFoundException,
)
from TileCache.Services.TMS import TMS

cfgfiles = (
    "/etc/tilecache.cfg",
    os.path.join("..", "tilecache.cfg"),
    "tilecache.cfg",
)


def import_module(name):
    """Helper module to import any module based on a name"""
    mod = __import__(name)
    components = name.split(".")
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


class Service(object):
    """Our Service Object"""

    __slots__ = (
        "layers",
        "cache",
        "metadata",
        "tilecache_options",
        "config",
        "files",
    )

    def __init__(self, cache, layers, metadata=None):
        """Constructor"""
        self.cache = cache
        self.layers = layers
        self.metadata = {} if metadata is None else metadata

    def _loadFromSection(cls, config, section, module, **objargs):
        """Unsure"""
        stype = config.get(section, "type")
        for opt in config.options(section):
            if opt not in ["type", "module"]:
                objargs[opt] = config.get(section, opt)

        object_module = None

        if config.has_option(section, "module"):
            object_module = import_module(config.get(section, "module"))
        else:
            if module is Layer:
                stype = stype.replace("Layer", "")
                object_module = import_module("TileCache.Layers.%s" % stype)
            else:
                stype = stype.replace("Cache", "")
                object_module = import_module("TileCache.Caches.%s" % stype)
        if object_module is None:
            raise TileCacheException("Attempt to load %s failed." % stype)

        section_object = getattr(object_module, stype)

        if module is Layer:
            return section_object(section, **objargs)
        return section_object(**objargs)

    loadFromSection = classmethod(_loadFromSection)

    def _load(cls, *files):
        """unsure"""
        cache = None
        metadata = {}
        layers = {}
        config = None
        try:
            config = configparser.ConfigParser()
            config.read(files)

            if config.has_section("metadata"):
                for key in config.options("metadata"):
                    metadata[key] = config.get("metadata", key)

            if config.has_section("tilecache_options"):
                if "path" in config.options("tilecache_options"):
                    for path in config.get("tilecache_options", "path").split(
                        ","
                    ):
                        sys.path.insert(0, path)

            cache = cls.loadFromSection(config, "cache", Cache)

            layers = {}
            for section in config.sections():
                if section in cls.__slots__:
                    continue
                layers[section] = cls.loadFromSection(
                    config, section, Layer, cache=cache
                )
        except Exception as exp:
            metadata["exception"] = exp
            metadata["traceback"] = str(exp)
        service = cls(cache, layers, metadata)
        service.files = files
        service.config = config
        return service

    load = classmethod(_load)

    def generate_crossdomain_xml(self):
        """Helper method for generating the XML content for a crossdomain.xml
        file, to be used to allow remote sites to access this content."""
        xml = [
            """<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM
  "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
        """
        ]
        if "crossdomain_sites" in self.metadata:
            sites = self.metadata["crossdomain_sites"].split(",")
            for site in sites:
                xml.append('  <allow-access-from domain="%s" />' % site)
        xml.append("</cross-domain-policy>")
        return ("text/xml", "\n".join(xml))

    def renderTile(self, tile, force=False):
        """render a Tile please"""
        layer = tile.layer

        # do more cache checking here: SRS, width, height, layers

        image = None
        if not force:
            image = self.cache.get(tile)
        if not image:
            data = layer.render(tile, force=force)
            if data:
                image = self.cache.set(tile, data)
            else:
                raise Exception("Zero length data returned from layer.")

        return (layer.mime_type, image)

    def dispatchRequest(
        self,
        params,
        path_info="/",
        req_method="GET",
        host="http://example.com/",
    ):
        """dispatch the request!"""
        if "exception" in self.metadata:
            raise TileCacheException(
                "%s\n%s"
                % (self.metadata["exception"], self.metadata["traceback"])
            )
        if path_info.find("crossdomain.xml") != -1:
            return self.generate_crossdomain_xml()

        tile = TMS(self).parse(params, path_info, host)
        if not hasattr(tile, "layer"):
            return "text/xml", tile.data.encode("utf-8")
        return self.renderTile(tile, "FORCE" in params)


def wsgiHandler(environ, start_response, service):
    """This is the WSGI handler"""

    host = ""
    path_info = environ.get("PATH_INFO", "")

    if "HTTP_X_FORWARDED_HOST" in environ:
        host = "http://" + environ["HTTP_X_FORWARDED_HOST"]
    elif "HTTP_HOST" in environ:
        host = "http://" + environ["HTTP_HOST"]

    host += environ["SCRIPT_NAME"]
    req_method = environ["REQUEST_METHOD"]

    try:
        fields = parse_formvars(environ)
        fmt, image = service.dispatchRequest(
            fields, path_info, req_method, host
        )
        headers = [("Content-Type", fmt)]
        if fmt.startswith("image/"):
            if service.cache.sendfile:
                headers.append(("X-SendFile", image))
            if service.cache.expire:
                headers.append(
                    (
                        "Expires",
                        email.utils.formatdate(
                            time.time() + service.cache.expire, False, True
                        ),
                    )
                )

        start_response("200 OK", headers)
        if service.cache.sendfile and fmt.startswith("image/"):
            return []
        return [image]
    except MalformedRequestException as exp:
        # reraise for others to handle
        raise InvalidTMSRequest(str(exp)) from exp
    except OutOfBoundsZoomLevel as exp:
        status = "422 Unprocessable Entity"
        msg = f"OutOfBoundsZoomLevel: {exp}"
    except TileCacheException as exp:
        status = "404 File Not Found"
        msg = f"An error occurred: {exp}"
    except TileCacheLayerNotFoundException as exp:
        status = "404 File Not Found"
        msg = f"TileCacheLayerNotFoundException: {exp}"
    except (BackendWMSFailure, TileCacheFutureException) as exp:
        status = "503 Service Unavailable"
        msg = f"{exp}"
    except Exception as exp:
        status = "500 Internal Server Error"
        E = str(exp)
        # Swallow this error
        if E.find("Corrupt, empty or missing file") == -1:
            emsg = E.replace("\n", " ")
            sys.stderr.write(
                f"TileCache Exception [client: {environ.get('REMOTE_ADDR')}] "
                f"Path: {path_info} "
                f"Err: {emsg} Referrer: {environ.get('HTTP_REFERER')}\n"
            )
            traceback.print_exc()
        msg = f"An error occurred: {exp}\n"

    start_response(status, [("Content-Type", "text/plain")])
    if isinstance(msg, string_types):
        msg = msg.encode("utf-8")
    return [msg]
