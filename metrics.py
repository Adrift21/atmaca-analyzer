"""Turns a flight into numbers. Today: the summary values shown as cards at the top of the page.

Typical change: add a summary card by adding one Metric line to summary().
"""
import pandas as pd

from models import Metric, Params


def summary(df: pd.DataFrame, params: Params) -> list[Metric]:
    """Information rows for the summary cards; the values are rounded for display."""
    flight_time_min = (df["time_s"].iloc[-1] - df["time_s"].iloc[0]) / 60
    mah_used = df["mah_drawn"].iloc[-1]
    remaining_pct = (params.capacity_mah - mah_used) / params.capacity_mah * 100
    return [
        Metric("", "Flight time", round(flight_time_min, 1), "min", "", None),
        Metric("", "Max distance", round(df["dist_m"].max(), 1), "m", "", None),
        Metric("", "Max altitude", round(df["alt_m"].max(), 1), "m", "", None),
        Metric("", "Used", round(mah_used), "mAh", "", None),
        Metric("", "Remaining", round(remaining_pct), "%", "", None),
        Metric("", "Min voltage", round(df["vbat_v"].min(), 1), "V", "", None),
        Metric("", "Min satellites", round(df["gps_sats"].min()), "sats", "", None),
    ]
