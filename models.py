"""The three small data containers of the program: safety parameters, events and metrics.

Typical change: add a field (e.g. a new safety parameter) and give it a value in config.DEFAULT_PARAMS.
"""
from dataclasses import dataclass


@dataclass
class Params:
    """Safety parameters loaded on the drone for this flight (entered in the sidebar)."""
    fence_radius_m: float         # R [m]
    fence_height_m: float         # H [m]
    release_margin_m: float       # m [m]
    confirm_s: float              # breach confirmation time [s]
    capacity_mah: float           # C [mAh]
    reserve: float                # r (0.20 = 20 %)
    landing_allowance_mah: float  # L [mAh]
    return_cost_mah_per_m: float  # k [mAh/m]
    warning_s: float              # battery warning time before the RTH [s]


@dataclass
class Event:
    """Something that happened at one moment of the flight."""
    time_s: float
    kind: str                     # ARM, DISARM, MODE, RTH_START, LINK_LOST, LINK_RESTORED, FAILSAFE_START,
                                  # FAILSAFE_END, FENCE_BREACH, FENCE_RELEASE, ALTITUDE_BREACH
    detail: str = ""              # e.g. the new mode, or the RTH reason
    lat: float | None = None
    lon: float | None = None


@dataclass
class Metric:
    """One row of the results: a measured value, its limit and whether it passed."""
    criterion: str                # "SC-2" … or "" for information rows
    name: str                     # e.g. "Hover drift RMS"
    value: float | None           # None when not tested in this flight
    unit: str
    limit: str                    # readable limit, e.g. "≤ 1.5"
    passed: bool | None           # None = N/A (this flight did not test the criterion)
