"""Reads a flight file into the normalized DataFrame (one row every 0.1 s, one flight).

Normalized CSV files (the samples) are read directly; INAV blackbox logs (.TXT/.BBL) are decoded once with
blackbox_decode and converted. Typical changes: a column header in config.COLUMN_MAP or a conversion rule below.
"""
import shutil
import subprocess
from pathlib import Path

import pandas as pd

import config
import geo


def list_log_files() -> list[Path]:
    """Return the flight files in samples/ and logs/ (sub-folders such as logs/decoded/ are skipped)."""
    files = []
    for folder in [config.SAMPLES_DIR, config.LOGS_DIR]:
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in config.LOG_EXTENSIONS:
                files.append(path)
    return files


def save_upload(name: str, data: bytes) -> Path:
    """Write an uploaded file into logs/ (only when it is new or changed) and return its path."""
    path = config.LOGS_DIR / name
    if not path.exists() or path.read_bytes() != data:
        config.LOGS_DIR.mkdir(exist_ok=True)
        path.write_bytes(data)
    return path


def flights_in_file(path: Path) -> list[Path]:
    """One CSV per flight: a normalized CSV is one flight; a blackbox log is decoded once into logs/decoded/."""
    if path.suffix.lower() == ".csv":
        return [path]
    out_dir = config.DECODED_DIR / path.stem
    if len(list(out_dir.glob("*.csv"))) == 0:
        decode_blackbox(path, out_dir)
    return sorted(out_dir.glob("*.csv"))


def decode_blackbox(path: Path, out_dir: Path) -> None:
    """Run blackbox_decode on a copy of the log in out_dir (the decoder writes its CSV files next to its input)."""
    if not config.DECODER_PATH.exists():
        raise ValueError(f"The blackbox decoder is missing. Download blackbox-tools-9.0.0_windows-x86_64.zip from "
                         f"{config.DECODER_URL} and copy bin/blackbox_decode.exe to {config.DECODER_PATH}.")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_copy = out_dir / path.name
    shutil.copyfile(path, log_copy)
    command = [str(config.DECODER_PATH)] + config.DECODER_ARGS + [str(log_copy)]
    result = subprocess.run(command, capture_output=True, text=True)
    log_copy.unlink()                            # keep only the decoder output
    if len(list(out_dir.glob("*.csv"))) == 0:    # the decoder exits with 0 even when it finds no flight
        raise ValueError(f"blackbox_decode found no flight in {path.name}: {result.stderr.strip()}")


def load_flight(csv_path: Path) -> pd.DataFrame:
    """Read a normalized or decoder CSV and return the normalized DataFrame with x_m, y_m and dist_m."""
    df = pd.read_csv(csv_path, dtype={"rth_reason": str}, skipinitialspace=True)
    if "time_s" not in df.columns:               # not a normalized CSV, so a blackbox_decode CSV
        df = normalize_decoder_csv(df)
    df["rth_reason"] = df["rth_reason"].fillna("")
    home_lat, home_lon = find_home(df)
    x, y = geo.to_xy_m(df["lat"], df["lon"], home_lat, home_lon)
    df["x_m"] = x
    df["y_m"] = y
    df["dist_m"] = (x ** 2 + y ** 2) ** 0.5
    return df


def find_home(df: pd.DataFrame) -> tuple[float, float]:
    """Return (lat, lon) of home: GPS_home of the log if it has one, otherwise the first row with a GPS fix."""
    lat_column, lon_column = "lat", "lon"
    if "home_lat" in df.columns:                 # decoded blackbox logs carry the home position
        lat_column, lon_column = "home_lat", "home_lon"
    for lat, lon in zip(df[lat_column], df[lon_column]):
        if pd.notna(lat) and pd.notna(lon) and lat != 0 and lon != 0:
            return float(lat), float(lon)
    raise ValueError("The flight has no row with a valid GPS fix, so home is unknown.")


# ---------------------------------------------------------------- INAV blackbox_decode CSV
def normalize_decoder_csv(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a blackbox_decode CSV into the normalized 10 Hz columns (rules in CLAUDE.md section 9.2)."""
    new_names = {}
    missing = []
    for name, header in config.COLUMN_MAP.items():
        new_names[header] = name
        if header not in raw.columns and name not in config.OPTIONAL_COLUMNS:
            missing.append(header)
    if len(missing) > 0:
        raise ValueError(f"columns missing in the decoder CSV: {', '.join(missing)} (see the Data section)")
    raw = raw.rename(columns=new_names)
    raw = raw.ffill()                            # empty GPS cells get the last value: GPS is slower than the FC
    raw["time_s"] = (raw["time_us"] - raw["time_us"].iloc[0]) / 1_000_000          # µs -> s since arming
    dt_s = raw["time_s"].diff().fillna(0)                                         # time since the previous row
    raw["mah_drawn"] = (raw["current_a"] * dt_s / 3.6).cumsum()   # A·s / 3.6 = mAh, as in tools/synthlog.py
    bins = (raw["time_s"] * config.SAMPLE_RATE_HZ).astype(int)    # number of the 0.1 s bin of every row
    rows = raw[~bins.duplicated()].reset_index(drop=True)          # keep the first row of every bin
    return normalized_columns(rows)


def normalized_columns(rows: pd.DataFrame) -> pd.DataFrame:
    """Build the normalized columns from the renamed decoder columns."""
    altitude_cm = rows["nav_alt_cm"] if "nav_alt_cm" in rows.columns else rows["baro_alt_cm"]
    df = pd.DataFrame({"time_s": rows["time_s"]})
    df["armed"] = 1                              # blackbox logs are written only while armed
    df["lat"] = rows["lat"]
    df["lon"] = rows["lon"]
    df["alt_m"] = (altitude_cm - altitude_cm.iloc[0]) / 100      # cm -> m above the take-off point
    df["ground_speed_ms"] = rows["ground_speed_ms"]
    df["vbat_v"] = rows["vbat_v"]
    df["current_a"] = rows["current_a"]
    df["mah_drawn"] = rows["mah_drawn"]
    df["flight_mode"] = [mode_from_flags(str(flags)) for flags in rows["mode_flags"]]
    df["rth_reason"] = ""                        # not in the log; events.py infers it
    df["failsafe"] = (rows["failsafe_phase"] != config.FAILSAFE_IDLE).astype(int)
    df["rc_link_ok"] = rows["rx_signal"]
    df["sticks_centered"] = sticks_centered(rows)
    df["gps_sats"] = rows["gps_sats"]
    if "home_lat" in rows.columns:
        df["home_lat"] = rows["home_lat"]
        df["home_lon"] = rows["home_lon"]
    return df


def mode_from_flags(flags: str) -> str:
    """ATMACA mode name from the flightModeFlags text: the first rule of config.MODE_RULES that matches."""
    for mode, flag in config.MODE_RULES:
        if flag in flags:
            return mode
    return "SPORT"                               # no assisted mode active: acro


def sticks_centered(rows: pd.DataFrame) -> pd.Series:
    """1 when roll, pitch and yaw are in their centre band and the throttle is in its (wider) band."""
    roll_ok = (rows["roll_us"] - config.STICK_CENTER_US).abs() <= config.STICK_DEADBAND_US
    pitch_ok = (rows["pitch_us"] - config.STICK_CENTER_US).abs() <= config.STICK_DEADBAND_US
    yaw_ok = (rows["yaw_us"] - config.STICK_CENTER_US).abs() <= config.STICK_DEADBAND_US
    throttle_ok = (rows["throttle_us"] - config.STICK_CENTER_US).abs() <= config.THROTTLE_DEADBAND_US
    return (roll_ok & pitch_ok & yaw_ok & throttle_ok).astype(int)


def column_report(csv_path: Path) -> list[tuple[str, str, bool]]:
    """For the "Data" section: (needed column, column header in the file, found?) for every expected column."""
    header = pd.read_csv(csv_path, nrows=0, skipinitialspace=True).columns
    report = []
    if "time_s" in header:                       # normalized CSV
        for column in config.NORMALIZED_COLUMNS:
            report.append((column, column, column in header))
    else:                                        # blackbox_decode CSV
        for name, column in config.COLUMN_MAP.items():
            report.append((name, column, column in header))
    return report
