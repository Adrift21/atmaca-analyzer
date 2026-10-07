"""Reads a flight file into the normalized DataFrame (one row every 0.1 s, one flight).

Today: normalized CSV files such as the synthetic samples (recognised by the column time_s).
Typical changes: where files are searched (paths in config.py) or how a derived column is computed.
"""
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


def load_flight(csv_path: Path) -> pd.DataFrame:
    """Read a normalized flight CSV and add the derived columns x_m, y_m and dist_m."""
    df = pd.read_csv(csv_path, dtype={"rth_reason": str})
    if "time_s" not in df.columns:
        raise ValueError(f"{csv_path.name} is not a normalized flight CSV (the column time_s is missing).")
    df["rth_reason"] = df["rth_reason"].fillna("")
    home_lat, home_lon = find_home(df)
    x, y = geo.to_xy_m(df["lat"], df["lon"], home_lat, home_lon)
    df["x_m"] = x
    df["y_m"] = y
    df["dist_m"] = (x ** 2 + y ** 2) ** 0.5
    return df


def find_home(df: pd.DataFrame) -> tuple[float, float]:
    """Return (lat, lon) of home: the first row with a valid GPS fix (position present and not 0)."""
    for lat, lon in zip(df["lat"], df["lon"]):
        if pd.notna(lat) and pd.notna(lon) and lat != 0 and lon != 0:
            return float(lat), float(lon)
    raise ValueError("The flight has no row with a valid GPS fix, so home is unknown.")
