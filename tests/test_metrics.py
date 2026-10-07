"""Tests for metrics.py: the values must reproduce the ground truth in samples/*.truth.json."""
import json

import config
import events
import loader
import metrics


def load_sample(name: str):
    """Return (DataFrame, truth dictionary) of one synthetic sample."""
    csv_path = config.SAMPLES_DIR / f"{name}.csv"
    truth = json.loads(csv_path.with_suffix(".truth.json").read_text())
    return loader.load_flight(csv_path), truth


def analyse(name: str):
    """Return (metric rows, events, truth) of one sample analysed with the default parameters."""
    df, truth = load_sample(name)
    found = events.find_events(df, config.DEFAULT_PARAMS)
    return metrics.compute_metrics(df, found, config.DEFAULT_PARAMS), found, truth


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


def test_hover_drift_matches_the_truth():
    for name in ["hover_before_tuning", "hover_after_tuning"]:
        df, _ = load_sample(name)
        assert len(metrics.hover_segments(df)) == 1, name
        rows, _, truth = analyse(name)
        assert abs(row_named(rows, "Hover drift RMS").value - truth["hover_drift_rms_m"]) < 0.05, name
        assert abs(row_named(rows, "Hover drift max").value - truth["hover_drift_max_m"]) < 0.05, name
        assert abs(row_named(rows, "Hover altitude RMS").value - truth["alt_hold_rms_m"]) < 0.05, name


def test_hover_before_tuning_fails_and_after_tuning_passes():
    before, _, _ = analyse("hover_before_tuning")
    after, _, _ = analyse("hover_after_tuning")
    assert row_named(before, "Hover drift RMS").passed is False
    assert row_named(after, "Hover drift RMS").passed is True


def test_fence_matches_the_truth():
    rows, _, truth = analyse("guest_fence")
    assert abs(row_named(rows, "Fence response").value - truth["fence_response_s"]) < 0.15
    assert abs(row_named(rows, "Fence release at").value - truth["release_s"]) < 0.15
    assert abs(row_named(rows, "Fence overshoot horizontal").value - truth["fence_overshoot_h_m"]) < 0.15
    assert abs(row_named(rows, "Fence overshoot vertical").value - truth["fence_overshoot_v_m"]) < 0.15


def test_battery_rth_matches_the_truth():
    rows, found, truth = analyse("battery_rth")
    rth = metrics.first_event(found, "RTH_START", "BATTERY")
    assert abs(rth.time_s - truth["rth_start_s"]) < 0.15
    assert abs(row_named(rows, "Battery threshold error").value - truth["battery_threshold_error_mah"]) < 3
    assert abs(row_named(rows, "Remaining after battery RTH").value - truth["remaining_mah"]) < 3
    assert abs(row_named(rows, "RTH landing error").value - truth["landing_error_m"]) < 0.15
    assert abs(row_named(rows, "Return cost k (measured)").value - truth["k_estimate_mAh_per_m"]) < 0.02


def test_failsafe_matches_the_truth():
    rows, _, truth = analyse("failsafe_rth")
    assert abs(row_named(rows, "Failsafe response").value - truth["failsafe_response_s"]) < 0.15
    assert abs(row_named(rows, "Link restored at").value - truth["link_restored_s"]) < 0.15
    assert abs(row_named(rows, "Control regained at").value - truth["control_regained_s"]) < 0.25


def test_criteria_not_tested_are_not_applicable():
    hover_rows, _, _ = analyse("hover_before_tuning")
    for name in ["Fence response", "Fence overshoot horizontal", "Fence overshoot vertical"]:
        assert row_named(hover_rows, name).value is None
        assert row_named(hover_rows, name).passed is None
    fence_rows, _, _ = analyse("guest_fence")
    assert row_named(fence_rows, "RTH landing error").value is None
    assert row_named(fence_rows, "Hover drift RMS").value is None
    assert row_named(fence_rows, "Time in NORMAL or SPORT").value is None       # flight shorter than 10 min


def test_touchdown_is_the_last_armed_row():
    """battery_rth lands 2.0 m from the take-off point (the truth's landing error)."""
    df, truth = load_sample("battery_rth")
    touchdown = metrics.last_armed_row(df)
    assert touchdown["armed"] == 1
    assert abs(touchdown["dist_m"] - truth["landing_error_m"]) < 0.15
