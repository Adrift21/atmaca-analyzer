"""Tests for loader.py and geo.py: a flight file becomes the normalized 10 Hz DataFrame."""
import json
from pathlib import Path

import pytest

import config
import geo
import loader
from tools.synthlog import COLUMNS

GUEST_FENCE = config.SAMPLES_DIR / "guest_fence.csv"
# Hand-written decoder CSV with the UNVERIFIED headers of config.COLUMN_MAP (20 Hz, 0.55 s);
# replace it with a cut of the first real bench log.
DECODER_FIXTURE = Path(__file__).parent / "fixtures" / "decoder_flight.csv"


# ---------------------------------------------------------------- normalized CSV (samples)
def test_list_log_files_finds_the_samples():
    names = [path.name for path in loader.list_log_files()]
    assert "guest_fence.csv" in names
    assert "guest_fence.truth.json" not in names


def test_normalized_columns_are_those_of_the_generator():
    assert config.NORMALIZED_COLUMNS == COLUMNS


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


def test_a_csv_file_is_one_flight():
    assert loader.flights_in_file(GUEST_FENCE) == [GUEST_FENCE]


# ---------------------------------------------------------------- INAV blackbox_decode CSV
def test_mode_from_flags():
    assert loader.mode_from_flags("ANGLE|NAVALTHOLD|NAVPOSHOLD") == "EASY"
    assert loader.mode_from_flags("ANGLE|NAVRTH") == "RTH"
    assert loader.mode_from_flags("ARM|ANGLE|NAVRTH|NAVPOSHOLD") == "RTH"     # the first rule wins
    assert loader.mode_from_flags("ANGLE") == "NORMAL"
    assert loader.mode_from_flags("0") == "SPORT"                            # no flag: acro


def test_decoder_csv_is_resampled_to_10_hz():
    df = loader.load_flight(DECODER_FIXTURE)
    assert list(df["time_s"].round(3)) == [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]


def test_mah_is_integrated_from_the_current():
    """36 A for 0.1 s = 3.6 A·s = 1 mAh per normalized row."""
    df = loader.load_flight(DECODER_FIXTURE)
    assert list(df["mah_drawn"].round(3)) == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def test_decoder_columns_are_converted():
    df = loader.load_flight(DECODER_FIXTURE)
    assert list(df["alt_m"].round(3)) == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    assert list(df["flight_mode"]) == ["EASY", "EASY", "RTH", "RTH", "NORMAL", "SPORT"]
    assert list(df["failsafe"]) == [0, 0, 1, 1, 0, 0]
    assert list(df["rc_link_ok"]) == [1, 1, 0, 0, 1, 1]
    assert list(df["sticks_centered"]) == [1, 1, 1, 0, 0, 0]
    assert list(df["gps_sats"]) == [12, 12, 11, 11, 10, 10]                  # GPS values are carried forward
    assert list(df["rth_reason"]) == [""] * 6
    assert abs(df["dist_m"].iloc[0] - 1.0) < 0.01                            # home = GPS_home, 1 m south


def test_column_report_finds_every_column():
    for csv_path in [DECODER_FIXTURE, GUEST_FENCE]:
        for needed, column, found in loader.column_report(csv_path):
            assert found, (csv_path.name, column)


def test_missing_decoder_gives_a_clear_message(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECODER_PATH", tmp_path / "bin" / "blackbox_decode.exe")
    monkeypatch.setattr(config, "DECODED_DIR", tmp_path / "decoded")
    log = tmp_path / "LOG00001.TXT"
    log.write_bytes(b"not a blackbox log")
    with pytest.raises(ValueError, match="decoder is missing"):
        loader.flights_in_file(log)


def test_a_file_without_flights_gives_a_clear_message(tmp_path, monkeypatch):
    if not config.DECODER_PATH.exists():
        pytest.skip("blackbox_decode.exe is not in tools/bin")
    monkeypatch.setattr(config, "DECODED_DIR", tmp_path / "decoded")
    log = tmp_path / "LOG00001.TXT"
    log.write_bytes(b"not a blackbox log")
    with pytest.raises(ValueError, match="found no flight"):
        loader.flights_in_file(log)


def test_save_upload_writes_into_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    path = loader.save_upload("LOG00002.TXT", b"log bytes")
    assert path == tmp_path / "logs" / "LOG00002.TXT"
    assert path.read_bytes() == b"log bytes"


# ---------------------------------------------------------------- geo.py
def test_to_xy_m_one_millidegree_north():
    x, y = geo.to_xy_m(41.001, 29.6, 41.0, 29.6)
    assert abs(x) < 1e-9
    assert abs(y - 111.32) < 0.01


def test_circle_points_are_at_the_radius():
    lats, lons = geo.circle_latlon(41.17, 29.6, 50.0)
    for lat, lon in zip(lats, lons):
        x, y = geo.to_xy_m(lat, lon, 41.17, 29.6)
        assert abs((x ** 2 + y ** 2) ** 0.5 - 50.0) < 0.01
