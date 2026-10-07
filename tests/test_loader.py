"""Tests for loader.py and geo.py: a flight file becomes the normalized 10 Hz DataFrame."""
import json

import config
import geo
import loader
from tools.synthlog import COLUMNS

GUEST_FENCE = config.SAMPLES_DIR / "guest_fence.csv"


def test_list_log_files_finds_the_samples():
    names = [path.name for path in loader.list_log_files()]
    assert "guest_fence.csv" in names
    assert "guest_fence.truth.json" not in names


def test_sample_loads_with_all_columns():
    df = loader.load_flight(GUEST_FENCE)
    for column in COLUMNS + ["x_m", "y_m", "dist_m"]:
        assert column in df.columns


def test_sample_has_ten_rows_per_second():
    df = loader.load_flight(GUEST_FENCE)
    duration_s = df["time_s"].iloc[-1] - df["time_s"].iloc[0]
    rows_per_second = (len(df) - 1) / duration_s
    assert abs(rows_per_second - config.SAMPLE_RATE_HZ) < 0.1


def test_missing_rth_reason_becomes_empty_text():
    df = loader.load_flight(GUEST_FENCE)
    assert df["rth_reason"].iloc[0] == ""


def test_distance_to_home_matches_the_truth():
    """Home is the first row; the farthest point is R plus the horizontal overshoot of the truth file."""
    df = loader.load_flight(GUEST_FENCE)
    truth = json.loads(GUEST_FENCE.with_suffix(".truth.json").read_text())
    farthest_m = truth["R_m"] + truth["fence_overshoot_h_m"]
    assert df["dist_m"].iloc[0] < 0.01
    assert abs(df["dist_m"].max() - farthest_m) < 0.05


def test_to_xy_m_one_millidegree_north():
    x, y = geo.to_xy_m(41.001, 29.6, 41.0, 29.6)
    assert abs(x) < 1e-9
    assert abs(y - 111.32) < 0.01


def test_circle_points_are_at_the_radius():
    lats, lons = geo.circle_latlon(41.17, 29.6, 50.0)
    for lat, lon in zip(lats, lons):
        x, y = geo.to_xy_m(lat, lon, 41.17, 29.6)
        assert abs((x ** 2 + y ** 2) ** 0.5 - 50.0) < 0.01
