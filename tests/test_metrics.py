"""Tests for metrics.py: the values must reproduce the ground truth in samples/*.truth.json."""
import json

import config
import loader
import metrics


def load_sample(name: str):
    """Return (DataFrame, truth dictionary) of one synthetic sample."""
    csv_path = config.SAMPLES_DIR / f"{name}.csv"
    truth = json.loads(csv_path.with_suffix(".truth.json").read_text())
    return loader.load_flight(csv_path), truth


def row_named(rows, name: str):
    """Return the metric row with this name."""
    for row in rows:
        if row.name == name:
            return row
    raise KeyError(name)


def test_battery_threshold_formula():
    """T(d) = C·(1 − r) − L − k·d; with the defaults 3000 · 0.8 − 150 − 0.9 · d."""
    assert abs(metrics.battery_threshold(config.DEFAULT_PARAMS, 0.0) - 2250.0) < 1e-6
    assert abs(metrics.battery_threshold(config.DEFAULT_PARAMS, 100.0) - 2160.0) < 1e-6


def test_summary_used_charge_matches_the_truth():
    df, truth = load_sample("battery_rth")
    used = row_named(metrics.summary(df, config.DEFAULT_PARAMS), "Used")
    assert abs(used.value - (truth["C_mAh"] - truth["remaining_mah"])) <= 1
