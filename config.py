"""All constants of the analyzer: paths, data rules, default safety parameters, analysis rules and the look.

Typical changes: a default parameter in DEFAULT_PARAMS, a success limit, a folder path, a colour or a size.
PARAMETERS describe what was loaded on the drone (they can differ per flight and are edited in the sidebar);
LIMITS are the project's success criteria (fixed in the RAD).
"""
from pathlib import Path

from models import Params

# ---------------------------------------------------------------- paths
PROJECT_DIR = Path(__file__).parent          # folder of this file
SAMPLES_DIR = PROJECT_DIR / "samples"        # synthetic flights with ground truth (do not edit)
LOGS_DIR = PROJECT_DIR / "logs"              # the user's real logs and uploads
LOG_EXTENSIONS = [".csv", ".txt", ".bbl"]    # file types listed in the sidebar (compared in lower case)
DECODED_DIR = LOGS_DIR / "decoded"           # blackbox_decode output, one folder per log (not committed)
DECODER_PATH = PROJECT_DIR / "tools" / "bin" / "blackbox_decode.exe"   # INAV blackbox-tools 9.0.0 (not committed)
DECODER_ARGS = ["--merge-gps"]               # GPS in the main CSV; default units are us, V, A, cm, m/s and flag names
DECODER_URL = "https://github.com/iNavFlight/blackbox-tools/releases/tag/v9.0.0"   # shown when the decoder is missing

# ---------------------------------------------------------------- data
SAMPLE_RATE_HZ = 10                          # rows per second of the normalized DataFrame [Hz]
NORMALIZED_COLUMNS = ["time_s", "armed", "lat", "lon", "alt_m", "ground_speed_ms", "vbat_v", "current_a",
                      "mah_drawn", "flight_mode", "rth_reason", "failsafe", "rc_link_ok", "sticks_centered",
                      "gps_sats"]            # columns of a normalized CSV (same as tools/synthlog.py)
# UNVERIFIED – check with the first bench log. Headers as blackbox_decode 9.0.0 writes them (field name, plus
# " (unit)" for converted fields) for the INAV 9.1 blackbox fields.
COLUMN_MAP = {                               # name used in loader.py -> column header in the decoder CSV
    "time_us": "time (us)",
    "vbat_v": "vbat (V)",
    "current_a": "amperage (A)",
    "roll_us": "rcData[0]",
    "pitch_us": "rcData[1]",
    "yaw_us": "rcData[2]",
    "throttle_us": "rcData[3]",
    "nav_alt_cm": "navPos[2]",
    "baro_alt_cm": "BaroAlt (cm)",
    "mode_flags": "flightModeFlags (flags)",
    "failsafe_phase": "failsafePhase (flags)",
    "rx_signal": "rxSignalReceived",
    "lat": "GPS_coord[0]",
    "lon": "GPS_coord[1]",
    "gps_sats": "GPS_numSat",
    "ground_speed_ms": "GPS_speed (m/s)",
    "home_lat": "GPS_home_lat",
    "home_lon": "GPS_home_lon",
}
OPTIONAL_COLUMNS = ["nav_alt_cm", "home_lat", "home_lon"]   # without them: BaroAlt, and home = first GPS fix
MODE_RULES = [                               # UNVERIFIED: (ATMACA mode, text in flightModeFlags), first match wins,
    ("RTH", "NAVRTH"),                       # no match = SPORT (acro); flag names as blackbox_decode 9.0.0 prints them
    ("EASY", "NAVPOSHOLD"),
    ("NORMAL", "ANGLE"),
]
FAILSAFE_IDLE = "IDLE"                       # failsafePhase text when no failsafe is active (UNVERIFIED)
STICK_CENTER_US = 1500                       # stick centre [µs]
STICK_DEADBAND_US = 30                       # roll, pitch, yaw count as centred within ± this [µs]
THROTTLE_DEADBAND_US = 50                    # throttle counts as centred ("hold altitude") within ± this [µs]
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

# ---------------------------------------------------------------- success-criteria LIMITS (fixed in the RAD)
SC2_RMS_MAX_M = 1.5                          # hover drift RMS [m]
SC2_MAX_M = 3.0                              # hover drift maximum [m]
SC2_ALT_RMS_MAX_M = 1.0                      # hover altitude RMS [m]
SC2_MIN_HOVER_S = 60                         # SC-2 needs a hover of at least this long [s]
SC3_LANDING_MAX_M = 3.0                      # RTH landing distance from home [m]
SC4_RESPONSE_MAX_S = 2.0                     # link loss -> failsafe RTH [s]
SC5_ERROR_MAX_MAH = 50                       # |mAh at the battery RTH trigger − T(d)| [mAh]
SC5_MIN_REMAINING = 0.20                     # charge left after a battery RTH [fraction of C]
SC6_RESPONSE_MAX_S = 1.0                     # confirmed fence breach -> fence RTH [s]
SC6_OVERSHOOT_H_MAX_M = 15                   # distance beyond R [m]
SC6_OVERSHOOT_V_MAX_M = 5                    # altitude above H [m]
SC8_MIN_FLIGHT_S = 600                       # SC-8 needs a flight of at least this long [s]
SC8_MIN_REMAINING = 0.20                     # charge left after the endurance flight [fraction of C]

# ---------------------------------------------------------------- analysis rules
HOVER_MIN_SEGMENT_S = 20                     # shortest hover segment (EASY, sticks centred, armed) [s]
HOVER_SETTLE_S = 2                           # the drift is measured from this long after the hover start [s]
RETURN_CLIMB_END_SPEED_MS = 1.0              # the RTH climb ends at the first row faster than this [m/s]
DESCENT_STEP_M = 0.05                        # the RTH descent starts at the first drop larger than this [m]
BATTERY_REASON_TOLERANCE_MAH = 20            # RTH reason inferred as BATTERY when mAh ≥ T(d) − this [mAh]

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
EVENT_COLOR = "gold"                         # event markers on the map
CURSOR_COLOR = "lime"                        # time cursor: marker on the map, vertical line on the charts
CURSOR_STEP_S = 1 / SAMPLE_RATE_HZ           # the time slider moves one row per step [s]
MAP_STYLE = "open-street-map"                # map tiles, need internet; "white-bg" works offline
MAP_HEIGHT = 500                             # height of the map [px]
MAP_MARGIN = {"l": 0, "r": 0, "t": 0, "b": 0}         # empty space around the map [px]
MAP_POINT_SIZE = 5                           # flight path points and release circle dots [px]
MAP_MARKER_SIZE = 14                         # home and touchdown markers [px]
MAP_EVENT_SIZE = 10                          # event markers [px]
MAP_ZOOM_RULE = [(90, 17), (180, 16), (370, 15), (750, 14), (1500, 13)]   # (flight stays within [m], zoom level)
MAP_ZOOM_FAR = 12                            # zoom level for flights farther than the last rule
RESULT_COLORS = {"PASS": "mediumseagreen", "FAIL": "red", "N/A": "grey", "INFO": "grey"}   # Result column
DATA_PREVIEW_ROWS = 20                       # rows shown in the "Data" section
