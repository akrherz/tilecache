# BSD Licensed, Copyright (c) 2006-2010 TileCache Contributors

import TileCache.Layer as Layer
from TileCache import OutOfBoundsZoomLevel
from TileCache.base import (
    Capabilities,
    MalformedRequestException,
    Request,
    TileCacheException,
)


class TMS(Request):
    """request"""

    def parse(self, fields, path, host):
        # /1.0.0/global_mosaic/0/0/0.jpg
        parts = list(filter(lambda x: x != "", path.split("/")))
        if not host[-1] == "/":
            host = host + "/"
        if len(parts) < 1:
            return self.serverCapabilities(host)
        if len(parts) < 2:
            return self.serviceCapabilities(host, self.service.layers)
        layer = self.getLayer(parts[1])
        if len(parts) < 5:
            return self.layerCapabilities(host, layer)
        if len(parts) > 5:
            raise MalformedRequestException("Too many path parts provided.")
        if parts[2] == "{z}":
            raise TileCacheException("{z} was provided instead of value.")
        parts[4] = parts[4].split(".")[0]
        tile = None
        try:
            zoom = round(float(parts[2]))
            x = int(parts[3])
            y = int(parts[4])
        except ValueError as exp:
            msg = f"Invalid, non-integer value provided: {exp}"
            raise MalformedRequestException(msg) from exp
        if layer.tms_type == "google" or fields.get("type") == "google":
            if zoom < 0 or zoom >= len(layer.resolutions):
                raise OutOfBoundsZoomLevel(zoom)
            res = layer.resolutions[zoom]
            maxY = (
                int(
                    round(
                        (layer.bbox[3] - layer.bbox[1]) / (res * layer.size[1])
                    )
                )
                - 1
            )
            tile = Layer.Tile(layer, x, maxY - y, zoom)
        else:
            tile = Layer.Tile(layer, x, y, zoom)
        return tile

    def serverCapabilities(self, host):
        return Capabilities(
            "text/xml",
            """<?xml version="1.0" encoding="UTF-8" ?>
            <Services>
                <TileMapService version="1.0.0" href="%s1.0.0/" />
            </Services>"""
            % host,
        )

    def serviceCapabilities(self, host, layers):
        xml = """<?xml version="1.0" encoding="UTF-8" ?>
            <TileMapService version="1.0.0">
              <TileMaps>"""

        for name, layer in layers.items():
            profile = "none"
            if layer.srs == "EPSG:4326":
                profile = "global-geodetic"
            elif layer.srs == "OSGEO:41001":
                profile = "global-mercator"
            xml += """
                <TileMap 
                   href="%s1.0.0/%s/" 
                   srs="%s"
                   title="%s"
                   profile="%s" />
                """ % (
                host,
                name,
                layer.srs,
                layer.name,
                profile,
            )

        xml += """
              </TileMaps>
            </TileMapService>"""

        return Capabilities("text/xml", xml)

    def layerCapabilities(self, host, layer):
        tms_type = layer.tms_type or "default"
        xml = """<?xml version="1.0" encoding="UTF-8" ?>
            <TileMap version="1.0.0" tilemapservice="%s1.0.0/">
              <!-- Additional data: tms_type is %s -->
              <Title>%s</Title>
              <Abstract>%s</Abstract>
              <SRS>%s</SRS>
              <BoundingBox minx="%.6f" miny="%.6f" maxx="%.6f" maxy="%.6f" />
              <Origin x="%.6f" y="%.6f" />  
            <TileFormat width="%d" height="%d" mime-type="%s" extension="%s" />
              <TileSets>
            """ % (
            host,
            tms_type,
            layer.name,
            layer.description,
            layer.srs,
            layer.bbox[0],
            layer.bbox[1],
            layer.bbox[2],
            layer.bbox[3],
            layer.bbox[0],
            layer.bbox[1],
            layer.size[0],
            layer.size[1],
            layer.fmt(),
            layer.extension,
        )

        for z, res in enumerate(layer.resolutions):
            xml += """
                 <TileSet href="%s1.0.0/%s/%d"
                          units-per-pixel="%.20f" order="%d" />""" % (
                host,
                layer.name,
                z,
                res,
                z,
            )

        xml += """
              </TileSets>
            </TileMap>"""

        return Capabilities("text/xml", xml)
