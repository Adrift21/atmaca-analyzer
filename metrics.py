"""Turns a flight into numbers: summary cards, the success criteria SC-2 … SC-8 and the measured return cost.

Typical changes: add a metric = write one function returning Metric rows and add one line to compute_metrics();
add a summary card = add one Metric line to summary(). All limits come from config.py.
"""
import pandas as pd

import config
import loader
from models import Event, Metric, Params


# ---------------------------------------------------------------- helpers
def battery_threshold(params: Params, dist_m: float | pd.Series) -> float | pd.Series:
    """T(d) = C·(1 − r) − L − k·d [mAh]: when the used charge reaches T(d), the battery RTH is due."""
    usable_mah = params.capacity_mah * (1 - params.reserve)
    return usable_mah - params.landing_allowance_mah - params.return_cost_mah_per_m * dist_m


def last_armed_row(df: pd.DataFrame) -> pd.Series:
    """The last row with the motors armed: the touchdown point of the flight."""
    return df[df["armed"] == 1].iloc[-1]


def first_event(events: list[Event], kind: str, detail: str = "", after_s: float = 0.0) -> Event | None:
    """The first event of this kind whose detail starts with `detail`, at or after after_s (None if none)."""
    for event in events:
        if event.kind == kind and event.detail.startswith(detail) and event.time_s >= after_s:
            return event
    return None


def first_time(rows: pd.DataFrame) -> float | None:
    """Time of the first of these rows (None if there are no rows)."""
    if len(rows) == 0:
        return None
    return rows["time_s"].iloc[0]


def duration_s(rows: pd.DataFrame) -> float:
    """Time from the first to the last of these rows."""
    return rows["time_s"].iloc[-1] - rows["time_s"].iloc[0]


def at_most(criterion: str, name: str, value: float | None, unit: str, limit: float) -> Metric:
    """A criterion row that passes when value ≤ limit (N/A when value is None)."""
    passed = None if value is None else bool(value <= limit)
    return Metric(criterion, name, value, unit, f"≤ {limit:g}", passed)


def at_least(criterion: str, name: str, value: float | None, unit: str, limit: float) -> Metric:
    """A criterion row that passes when value ≥ limit (N/A when value is None)."""
    passed = None if value is None else bool(value >= limit)
    return Metric(criterion, name, value, unit, f"≥ {limit:g}", passed)


# ---------------------------------------------------------------- summary cards
def summary(df: pd.DataFrame, params: Params) -> list[Metric]:
    """Information rows for the summary cards; the values are rounded for display."""
    mah_used = df["mah_drawn"].iloc[-1]
    remaining_pct = (params.capacity_mah - mah_used) / params.capacity_mah * 100
    return [
        Metric("", "Flight time", round(duration_s(df) / 60, 1), "min", "", None),
        Metric("", "Max distance", round(df["dist_m"].max(), 1), "m", "", None),
        Metric("", "Max altitude", round(df["alt_m"].max(), 1), "m", "", None),
        Metric("", "Used", round(mah_used), "mAh", "", None),
        Metric("", "Remaining", round(remaining_pct), "%", "", None),
        Metric("", "Min voltage", round(df["vbat_v"].min(), 1), "V", "", None),
        Metric("", "Min satellites", round(df["gps_sats"].min()), "sats", "", None),
    ]


# ---------------------------------------------------------------- success criteria
def compute_metrics(df: pd.DataFrame, events: list[Event], params: Params) -> list[Metric]:
    """All rows of the success-criteria table, in this order."""
    rows = []
    rows += hover_drift(df)
    rows += landing_error(df, events)
    rows += failsafe_response(df, events)
    rows += battery_rth(df, events, params)
    rows += fence(df, events, params)
    rows += return_cost(df, events)
    rows += endurance(df, params)
    return rows


def hover_segments(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Parts where the drone holds position (EASY, sticks centred, armed) for ≥ HOVER_MIN_SEGMENT_S."""
    holding = (df["flight_mode"] == "EASY") & (df["sticks_centered"] == 1) & (df["armed"] == 1)
    segments = []
    start = None                                 # row number where the current hold began
    for number, is_holding in enumerate(list(holding) + [False]):   # the extra False ends a hold at the end
        if is_holding and start is None:
            start = number
        elif not is_holding and start is not None:
            segment = df.iloc[start:number]
            if duration_s(segment) >= config.HOVER_MIN_SEGMENT_S:
                segments.append(segment)
            start = None
    return segments


def hover_drift(df: pd.DataFrame) -> list[Metric]:
    """SC-2: how far the drone wanders from the hold point in the longest hover (N/A if shorter than 60 s)."""
    rms_m = max_m = altitude_rms_m = None
    longest = max(hover_segments(df), key=duration_s, default=None)    # None when there is no hover
    if longest is not None and duration_s(longest) >= config.SC2_MIN_HOVER_S:
        hold = longest.iloc[0]                   # the hold point: position and altitude at the start
        settled = longest[longest["time_s"] >= hold["time_s"] + config.HOVER_SETTLE_S]
        drift_m = ((settled["x_m"] - hold["x_m"]) ** 2 + (settled["y_m"] - hold["y_m"]) ** 2) ** 0.5
        altitude_error_m = settled["alt_m"] - hold["alt_m"]
        rms_m = (drift_m ** 2).mean() ** 0.5
        max_m = drift_m.max()
        altitude_rms_m = (altitude_error_m ** 2).mean() ** 0.5
    return [
        at_most("SC-2", "Hover drift RMS", rms_m, "m", config.SC2_RMS_MAX_M),
        at_most("SC-2", "Hover drift max", max_m, "m", config.SC2_MAX_M),
        at_most("SC-2", "Hover altitude RMS", altitude_rms_m, "m", config.SC2_ALT_RMS_MAX_M),
    ]


def landing_error(df: pd.DataFrame, events: list[Event]) -> list[Metric]:
    """SC-3: distance from home where an RTH landed (N/A when the flight did not end in RTH)."""
    touchdown = last_armed_row(df)
    error_m = None
    if first_event(events, "RTH_START") is not None and touchdown["flight_mode"] == "RTH":
        error_m = touchdown["dist_m"]
    return [at_most("SC-3", "RTH landing error", error_m, "m", config.SC3_LANDING_MAX_M)]


def failsafe_response(df: pd.DataFrame, events: list[Event]) -> list[Metric]:
    """SC-4: link loss -> failsafe RTH; information: when the link and the pilot's control came back."""
    lost = first_event(events, "LINK_LOST")
    rth = first_event(events, "RTH_START", "FAILSAFE")
    response_s = restored_s = regained_s = None
    if lost is not None and rth is not None:
        after_rth = df[df["time_s"] > rth.time_s]
        response_s = rth.time_s - lost.time_s
        restored_s = first_time(after_rth[after_rth["rc_link_ok"] == 1])
        pilot_rows = after_rth[(after_rth["flight_mode"] != "RTH") & (after_rth["flight_mode"] != "LAND")]
        regained_s = first_time(pilot_rows)
    return [
        at_most("SC-4", "Failsafe response", response_s, "s", config.SC4_RESPONSE_MAX_S),
        Metric("SC-4", "Link restored at", restored_s, "s", "", None),
        Metric("SC-4", "Control regained at", regained_s, "s", "", None),
    ]


def battery_rth(df: pd.DataFrame, events: list[Event], params: Params) -> list[Metric]:
    """SC-5: used charge against T(d) when the battery warning started, and the charge left after landing."""
    error_mah = remaining_mah = None
    rth = first_event(events, "RTH_START", "BATTERY")
    if rth is not None:
        trigger = loader.nearest_row(df, rth.time_s - params.warning_s)   # when the battery warning started
        error_mah = trigger["mah_drawn"] - battery_threshold(params, trigger["dist_m"])
        remaining_mah = params.capacity_mah - df["mah_drawn"].iloc[-1]
    error_passed = None if error_mah is None else bool(abs(error_mah) <= config.SC5_ERROR_MAX_MAH)
    min_remaining_mah = params.capacity_mah * config.SC5_MIN_REMAINING
    return [
        Metric("SC-5", "Battery threshold error", error_mah, "mAh", f"± {config.SC5_ERROR_MAX_MAH:g}", error_passed),
        at_least("SC-5", "Remaining after battery RTH", remaining_mah, "mAh", min_remaining_mah),
    ]


def fence(df: pd.DataFrame, events: list[Event], params: Params) -> list[Metric]:
    """SC-6: reaction to a confirmed fence breach, and how far the drone went beyond R and H."""
    response_s = release_s = overshoot_h_m = overshoot_v_m = fence_rth = None     # stay None without a breach
    breach = first_event(events, "FENCE_BREACH")
    if breach is not None:
        first_exceed_s = breach.time_s - params.confirm_s
        fence_rth = first_event(events, "RTH_START", "FENCE", first_exceed_s)
        episode = df[df["time_s"] >= first_exceed_s]                   # until the release or the end of flight
        if fence_rth is not None:
            response_s = fence_rth.time_s - breach.time_s
            release = first_event(events, "FENCE_RELEASE", "", fence_rth.time_s)
            if release is not None:
                release_s = release.time_s
                episode = episode[episode["time_s"] <= release_s]
        overshoot_h_m = episode["dist_m"].max() - params.fence_radius_m
        overshoot_v_m = max(0.0, episode["alt_m"].max() - params.fence_height_m)
    response = at_most("SC-6", "Fence response", response_s, "s", config.SC6_RESPONSE_MAX_S)
    if breach is not None and fence_rth is None:                       # breach confirmed, but no fence RTH
        response = Metric("SC-6", "Fence response (no fence RTH)", None, "s", response.limit, False)
    return [
        response,
        at_most("SC-6", "Fence overshoot horizontal", overshoot_h_m, "m", config.SC6_OVERSHOOT_H_MAX_M),
        at_most("SC-6", "Fence overshoot vertical", overshoot_v_m, "m", config.SC6_OVERSHOOT_V_MAX_M),
        Metric("SC-6", "Fence release at", release_s, "s", "", None),
    ]


def return_cost(df: pd.DataFrame, events: list[Event]) -> list[Metric]:
    """Return cost k measured in this flight: charge per metre flown home between the RTH climb and descent."""
    k = None
    rth = first_event(events, "RTH_START")
    if rth is not None:
        rth_rows = df[(df["time_s"] >= rth.time_s) & (df["flight_mode"] == "RTH")]
        cruising = rth_rows[rth_rows["ground_speed_ms"] > config.RETURN_CLIMB_END_SPEED_MS]
        if len(cruising) > 0:
            climb_end = cruising.iloc[0]
            later = rth_rows[rth_rows["time_s"] > climb_end["time_s"]]
            previous_alt = later["alt_m"].shift(1)                     # altitude of the previous row
            descending = later[previous_alt - later["alt_m"] > config.DESCENT_STEP_M]
            if len(descending) > 0:
                k = (descending["mah_drawn"].iloc[0] - climb_end["mah_drawn"]) / climb_end["dist_m"]
    return [Metric("", "Return cost k (measured)", k, "mAh/m", "", None)]


def endurance(df: pd.DataFrame, params: Params) -> list[Metric]:
    """SC-8: a flight of ≥ 10 min in assisted modes only (no NORMAL or SPORT) that ends with ≥ 20 % left."""
    manual_s = remaining_pct = None
    if duration_s(df) >= config.SC8_MIN_FLIGHT_S:
        manual_rows = df[(df["flight_mode"] == "NORMAL") | (df["flight_mode"] == "SPORT")]
        manual_s = len(manual_rows) / config.SAMPLE_RATE_HZ
        remaining_pct = (params.capacity_mah - df["mah_drawn"].iloc[-1]) / params.capacity_mah * 100
    return [
        at_most("SC-8", "Time in NORMAL or SPORT", manual_s, "s", 0),
        at_least("SC-8", "Remaining after endurance flight", remaining_pct, "%", config.SC8_MIN_REMAINING * 100),
    ]
