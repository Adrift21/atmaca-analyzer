"""All constants of the analyzer: paths, data rules, the default safety parameters and the look of the page.

Typical changes: a default parameter in DEFAULT_PARAMS, a folder path, a colour or a chart size.
PARAMETERS describe what was loaded on the drone (they can differ per flight and are edited in the sidebar).
"""
from pathlib import Path

from models import Params

# ---------------------------------------------------------------- paths
PROJECT_DIR = Path(__file__).parent          # folder of this file
SAMPLES_DIR = PROJECT_DIR / "samples"        # synthetic flights with ground truth (do not edit)
LOGS_DIR = PROJECT_DIR / "logs"              # the user's real logs and uploads
LOG_EXTENSIONS = [".csv", ".txt", ".bbl"]    # file types listed in the sidebar (compared in lower case)

# ---------------------------------------------------------------- data
SAMPLE_RATE_HZ = 10                          # rows per second of the normalized DataFrame [Hz]
METERS_PER_DEG_LAT = 111_320.0               # metres per degree of latitude [m/°]
CIRCLE_POINTS = 72                           # points used to draw one circle on the map

# ---------------------------------------------------------------- default safety PARAMETERS (sidebar start values)
DEFAULT_PARAMS = Params(
    fence_radius_m=50.0,                     # R: fence radius around home [m]
    fence_height_m=30.0,                     # H: fence altitude above home [m]
    release_margin_m=15.0,                   # m: the fence RTH ends inside R − m [m]
    confirm_s=1.0,                           # breach confirmation time [s]
    capacity_mah=3000.0,                     # C: battery capacity [mAh]
    reserve=0.20,                            # r: landing reserve [fraction of C]
    landing_allowance_mah=150.0,             # L: charge needed for the descent and landing [mAh]
    return_cost_mah_per_m=0.9,               # k: charge per metre of the way home [mAh/m]
    warning_s=5.0,                           # warning time before the battery RTH [s]
)

# ---------------------------------------------------------------- look
CHART_HEIGHT = 280                           # height of one time chart [px]
CHART_MARGIN = {"l": 10, "r": 10, "t": 40, "b": 10}   # empty space around a chart [px]
REFERENCE_LINE_COLOR = "red"                 # horizontal limit lines on the charts (R, H, …)

MODE_COLORS = {                              # colour of the map points per flight mode
    "EASY": "green",
    "NORMAL": "blue",
    "SPORT": "purple",
    "RTH": "deeppink",
    "LAND": "brown",
}
PATH_COLOR = "grey"                          # line of the flight path on the map
FENCE_COLOR = "red"                          # fence circle R on the map
RELEASE_COLOR = "orange"                     # release circle R − m on the map (drawn as dots)
HOME_COLOR = "black"                         # home marker
TOUCHDOWN_COLOR = "darkcyan"                 # touchdown marker (last armed row)
MAP_STYLE = "open-street-map"                # map tiles, need internet; "white-bg" works offline
MAP_HEIGHT = 500                             # height of the map [px]
MAP_MARGIN = {"l": 0, "r": 0, "t": 0, "b": 0}         # empty space around the map [px]
MAP_POINT_SIZE = 5                           # flight path points and release circle dots [px]
MAP_MARKER_SIZE = 14                         # home and touchdown markers [px]
MAP_ZOOM_RULE = [(90, 17), (180, 16), (370, 15), (750, 14), (1500, 13)]   # (flight stays within [m], zoom level)
MAP_ZOOM_FAR = 12                            # zoom level for flights farther than the last rule
