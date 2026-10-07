"""Flat-earth geometry: GPS degrees to metres around home, and the points of a circle for the map.

Equirectangular approximation: accurate enough within a few kilometres and easy to explain.
Typical change: none (the constants are in config.py).
"""
import math

import pandas as pd

import config


def meters_per_deg_lon(home_lat: float) -> float:
    """Metres per degree of longitude: shorter than for latitude by cos(latitude)."""
    return config.METERS_PER_DEG_LAT * math.cos(math.radians(home_lat))


def to_xy_m(lat: float | pd.Series, lon: float | pd.Series,
            home_lat: float, home_lon: float) -> tuple[float | pd.Series, float | pd.Series]:
    """Return (x east, y north) in metres from home; works for single numbers and whole columns."""
    x = (lon - home_lon) * meters_per_deg_lon(home_lat)
    y = (lat - home_lat) * config.METERS_PER_DEG_LAT
    return x, y


def circle_latlon(home_lat: float, home_lon: float, radius_m: float,
                  points: int = config.CIRCLE_POINTS) -> tuple[list[float], list[float]]:
    """Return (lats, lons) of a closed circle of radius_m around home."""
    lats = []
    lons = []
    for i in range(points + 1):              # one extra point closes the circle
        angle = 2 * math.pi * i / points
        lats.append(home_lat + radius_m * math.sin(angle) / config.METERS_PER_DEG_LAT)
        lons.append(home_lon + radius_m * math.cos(angle) / meters_per_deg_lon(home_lat))
    return lats, lons
