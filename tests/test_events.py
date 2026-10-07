"""Tests for events.py: event times of the synthetic flights and the RTH reason inference."""
import json
from dataclasses import replace

import config
import events
import loader

TOLERANCE_S = 0.15        # the samples log the last row before a change; the detector finds the first row after it


def load_sample(name: str):
    """Return (DataFrame, truth dictionary) of one synthetic sample."""
    csv_path = config.SAMPLES_DIR / f"{name}.csv"
    truth = json.loads(csv_path.with_suffix(".truth.json").read_text())
    return loader.load_flight(csv_path), truth


def first_of(found: list, kind: str):
    """Return the first event of this kind."""
    for event in found:
        if event.kind == kind:
            return event
    raise KeyError(kind)


def test_guest_fence_event_times():
    df, truth = load_sample("guest_fence")
    found = events.find_events(df, config.DEFAULT_PARAMS)
    breach = first_of(found, "FENCE_BREACH")
    rth = first_of(found, "RTH_START")
    assert abs(breach.time_s - (truth["breach_first_exceed_s"] + truth["confirm_s"])) < TOLERANCE_S
    assert rth.detail == "FENCE"
    assert abs(rth.time_s - truth["rth_start_s"]) < TOLERANCE_S
    assert abs(first_of(found, "FENCE_RELEASE").time_s - truth["release_s"]) < TOLERANCE_S
    assert found[0].kind == "ARM"
    assert found[-1].kind == "DISARM"


def test_failsafe_event_times():
    df, truth = load_sample("failsafe_rth")
    found = events.find_events(df, config.DEFAULT_PARAMS)
    rth = first_of(found, "RTH_START")
    assert abs(first_of(found, "LINK_LOST").time_s - truth["link_lost_s"]) < TOLERANCE_S
    assert rth.detail == "FAILSAFE"
    assert abs(rth.time_s - truth["rth_start_s"]) < TOLERANCE_S
    assert abs(first_of(found, "LINK_RESTORED").time_s - truth["link_restored_s"]) < TOLERANCE_S


def test_events_are_sorted_by_time():
    df, _ = load_sample("failsafe_rth")
    times = [event.time_s for event in events.find_events(df, config.DEFAULT_PARAMS)]
    assert times == sorted(times)


def test_rth_reason_is_inferred_when_the_log_has_none():
    expected = {"guest_fence": "FENCE", "failsafe_rth": "FAILSAFE", "battery_rth": "BATTERY"}
    for name, reason in expected.items():
        df, _ = load_sample(name)
        df["rth_reason"] = ""
        rth = first_of(events.find_events(df, config.DEFAULT_PARAMS), "RTH_START")
        assert rth.detail == f"{reason} (inferred)", name


def test_altitude_breach_only_above_h():
    df, _ = load_sample("guest_fence")                       # flies at 8 m
    default_kinds = [event.kind for event in events.find_events(df, config.DEFAULT_PARAMS)]
    assert "ALTITUDE_BREACH" not in default_kinds
    low_fence = replace(config.DEFAULT_PARAMS, fence_height_m=5.0)
    low_fence_kinds = [event.kind for event in events.find_events(df, low_fence)]
    assert "ALTITUDE_BREACH" in low_fence_kinds
