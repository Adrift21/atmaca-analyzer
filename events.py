"""Finds the events of a flight: arming, mode changes, RTH, link loss, failsafe and limit breaches.

Each detector is one small function that compares a row with the previous row.
Typical change: add an event = write one detector function and add one line to find_events().
"""
import pandas as pd

import config
import metrics
from models import Event, Params


def find_events(df: pd.DataFrame, params: Params) -> list[Event]:
    """All events of the flight, sorted by time."""
    rows = df.to_dict("records")                 # one dictionary per row, e.g. rows[0]["time_s"]
    found = [make_event(rows[0], "ARM", rows[0]["flight_mode"])]
    found += transitions(rows, "armed", 1, 0, "DISARM")
    found += mode_changes(rows)
    found += rth_starts(rows, params)
    found += transitions(rows, "rc_link_ok", 1, 0, "LINK_LOST")
    found += transitions(rows, "rc_link_ok", 0, 1, "LINK_RESTORED")
    found += transitions(rows, "failsafe", 0, 1, "FAILSAFE_START")
    found += transitions(rows, "failsafe", 1, 0, "FAILSAFE_END")
    found += limit_breaches(rows, "dist_m", params.fence_radius_m, params.confirm_s, "FENCE_BREACH")
    found += limit_breaches(rows, "alt_m", params.fence_height_m, params.confirm_s, "ALTITUDE_BREACH")
    found += fence_releases(found)
    found.sort(key=event_time)
    return found


def make_event(row: dict, kind: str, detail: str = "") -> Event:
    """An event at the time and position of this row."""
    return Event(row["time_s"], kind, detail, row["lat"], row["lon"])


def event_time(event: Event) -> float:
    """Sort key: the time of an event."""
    return event.time_s


def transitions(rows: list[dict], column: str, old: int, new: int, kind: str) -> list[Event]:
    """Events at the rows where the column changes from old to new."""
    found = []
    for previous, row in zip(rows, rows[1:]):    # pairs (previous row, row)
        if previous[column] == old and row[column] == new:
            found.append(make_event(row, kind))
    return found


def mode_changes(rows: list[dict]) -> list[Event]:
    """MODE events where the flight mode differs from the previous row; detail = the new mode."""
    found = []
    for previous, row in zip(rows, rows[1:]):
        if row["flight_mode"] != previous["flight_mode"]:
            found.append(make_event(row, "MODE", row["flight_mode"]))
    return found


def rth_starts(rows: list[dict], params: Params) -> list[Event]:
    """RTH_START where the mode becomes RTH; detail = the logged reason, or the inferred one."""
    found = []
    for previous, row in zip(rows, rows[1:]):
        if previous["flight_mode"] != "RTH" and row["flight_mode"] == "RTH":
            reason = row["rth_reason"]
            if reason == "":
                reason = infer_rth_reason(row, params) + " (inferred)"
            found.append(make_event(row, "RTH_START", reason))
    return found


def infer_rth_reason(row: dict, params: Params) -> str:
    """Why the RTH started, for logs without a reason (real INAV logs); the checks run in this order."""
    if row["failsafe"] == 1:
        return "FAILSAFE"
    threshold_mah = metrics.battery_threshold(params, row["dist_m"])
    if row["mah_drawn"] >= threshold_mah - config.BATTERY_REASON_TOLERANCE_MAH:
        return "BATTERY"
    if row["dist_m"] > params.fence_radius_m:
        return "FENCE"
    return "PILOT"


def limit_breaches(rows: list[dict], column: str, limit: float, confirm_s: float, kind: str) -> list[Event]:
    """Events where the column stays above the limit for confirm_s; time = first exceeding row + confirm_s."""
    found = []
    first_exceed = None                          # the row where the current exceedance began
    reported = False                             # True when this exceedance already has its event
    for row in rows:
        if row[column] <= limit:
            first_exceed = None
            continue
        if first_exceed is None:
            first_exceed = row
            reported = False
        if not reported and row["time_s"] - first_exceed["time_s"] >= confirm_s:
            breach_s = first_exceed["time_s"] + confirm_s
            found.append(Event(breach_s, kind, f"{column} > {limit:g}", row["lat"], row["lon"]))
            reported = True
    return found


def fence_releases(events: list[Event]) -> list[Event]:
    """FENCE_RELEASE at the first change to EASY after each RTH_START with reason FENCE."""
    releases = []
    waiting = False                              # True after a fence RTH until the pilot is back in EASY
    for event in sorted(events, key=event_time):
        if event.kind == "RTH_START" and event.detail.startswith("FENCE"):
            waiting = True
        elif waiting and event.kind == "MODE" and event.detail == "EASY":
            releases.append(Event(event.time_s, "FENCE_RELEASE", "", event.lat, event.lon))
            waiting = False
    return releases


def events_table(events: list[Event]) -> pd.DataFrame:
    """The events as a table for the page: time [s] with one decimal, event, detail."""
    table_rows = []
    for event in events:
        table_rows.append({"Time [s]": round(event.time_s, 1), "Event": event.kind, "Detail": event.detail})
    return pd.DataFrame(table_rows)
