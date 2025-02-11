"""Baseline objects to allow cleaner imports"""

import copy
from datetime import datetime, timedelta, timezone


class MalformedRequestException(Exception):
    """Exception raised when a request is malformed"""


class TileCacheException(Exception):
    """Exception"""


class TileCacheLayerNotFoundException(Exception):
    """Exception"""


class TileCacheFutureException(Exception):
    """Exception"""


class Capabilities(object):
    """object"""

    def __init__(self, fmt, data):
        """Constructor"""
        self.fmt = fmt
        self.data = data


class Request(object):
    """object"""

    def __init__(self, service):
        """Constructor"""
        self.service = service

    def getLayer(self, layername):
        """implements some custom logic here for the provided layername"""
        # GH33 remove 20 some year legacy of having -900913 in the layername
        layername = layername.replace("-900913", "")
        layer = self.service.layers.get(layername)
        # If the layername is known, there is no logic to implement
        if layer is not None:
            return layer
        if layername.startswith("idep"):
            (lbl, ltype, date) = layername.split("::", 3)
            scenario = lbl[4:]
            uri = ("date=%s&year=%s&month=%s&day=%s&scenario=%s") % (
                date,
                date[:4],
                date[5:7],
                date[8:10],
                scenario,
            )
            layer = copy.copy(self.service.layers["idep"])
            layer.name = layername
            layer.layers = ltype
            layer.url = "%s%s" % (layer.metadata["baseurl"], uri)
        elif layername.startswith("goes_"):
            (_bogus, bird, sector, channel) = layername.split("_")
            layer = copy.copy(self.service.layers["goes_%s" % (bird,)])
            layer.name = layername
            layer.layers = "%s_%s" % (sector, channel)
        elif layername.startswith("mrms::"):
            # mrms::a2m-202307101700
            (prod, tstring) = (layername.split("::")[1]).split("-")
            if len(tstring) == 12:
                mylayername = "mrms-t"
                uri = (
                    f"year={tstring[:4]}&month={tstring[4:6]}"
                    f"&day={tstring[6:8]}&time={tstring[8:12]}&"
                )
            else:
                mylayername = "mrms"
                uri = ""
            layer = copy.copy(self.service.layers[mylayername])
            layer.name = layername
            layer.url = f"{layer.metadata['baseurl']}prod={prod.lower()}&{uri}"
        elif layername.startswith("goes::"):
            (bird, channel, tstring) = (layername.split("::")[1]).split("-")
            if len(tstring) == 12:
                mylayername = "goes-t"
                year = tstring[:4]
                month = tstring[4:6]
                day = tstring[6:8]
                ts = tstring[8:12]
                uri = "year=%s&month=%s&day=%s&time=%s&" % (
                    year,
                    month,
                    day,
                    ts,
                )
            else:
                mylayername = "goes"
                uri = ""
            layer = copy.copy(self.service.layers[mylayername])
            layer.name = layername
            layer.url = "%sbird=%s&channel=%s&%s" % (
                layer.metadata["baseurl"],
                bird,
                channel,
                uri,
            )
        elif layername.startswith("hrrr::"):
            (prod, ftime, tstring) = (layername.split("::")[1]).split("-")
            ptype = "d" if layername.find("REFD") > 0 else "p"
            if len(tstring) == 12:
                mylayername = f"hrrr-ref{ptype}-t"
                mslayer = f"ref{ptype}-t"
                year = tstring[:4]
                month = tstring[4:6]
                day = tstring[6:8]
                hour = tstring[8:10]
                uri = ("year=%s&month=%s&day=%s&hour=%s&f=%s") % (
                    year,
                    month,
                    day,
                    hour,
                    ftime[1:],
                )
            else:
                mylayername = f"hrrr-ref{ptype}"
                mslayer = f"ref{ptype}_{ftime[1:]}"
                uri = ""
            layer = copy.copy(self.service.layers[mylayername])
            layer.name = layername
            layer.layers = mslayer
            layer.url = "%s%s" % (layer.metadata["baseurl"], uri)
        elif layername.find("::") > 0:
            (sector, prod, tstring) = (layername.split("::")[1]).split("-")
            if len(tstring) == 12:
                utcnow = (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).strftime("%Y%m%d%H%M")
                if tstring > utcnow:
                    raise TileCacheFutureException(
                        "Specified time in the future!"
                    )
                mylayername = "ridge-t"
                year = tstring[:4]
                month = tstring[4:6]
                day = tstring[6:8]
                ts = tstring[8:12]
                if sector in ["USCOMP", "HICOMP", "AKCOMP", "PRCOMP"]:
                    mylayername = "ridge-composite-t"
                    if prod == "N0R":
                        mylayername = "ridge-composite-t-n0r"
                    sector = sector.lower()
                    prod = prod.lower()
                    # these should always be for a minutes mod 5
                    # if not, save the users from themselves
                    if ts[-1] not in ["0", "5"]:
                        extra = "5" if ts[-1] > "5" else "0"
                        ts = "%s%s" % (ts[:3], extra)
                uri = "year=%s&month=%s&day=%s&time=%s&" % (
                    year,
                    month,
                    day,
                    ts,
                )
            else:
                if sector in ["USCOMP", "HICOMP", "AKCOMP", "PRCOMP"]:
                    prod = prod.lower()
                    mylayername = "ridge-composite-single"
                else:
                    mylayername = "ridge-single"
                uri = ""
            layer = copy.copy(self.service.layers[mylayername])
            layer.name = layername
            layer.url = "%ssector=%s&prod=%s&%s" % (
                layer.metadata["baseurl"],
                sector,
                prod,
                uri,
            )
        if layer is None:
            raise TileCacheLayerNotFoundException(
                f"Layer {layername} not found"
            )
        return layer
