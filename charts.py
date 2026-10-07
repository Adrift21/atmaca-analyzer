"""Plotly figures of the page: the time-series charts below the map.

Typical changes: add a chart (one small function here, one line in app.py), change a title, unit or limit line.
"""
import pandas as pd
import plotly.graph_objects as go

import config
import metrics
from models import Params


def time_chart(df: pd.DataFrame, column: str, title: str, unit: str,
               lines: list[tuple[float, str]]) -> go.Figure:
    """Line chart of one column over time, with horizontal reference lines given as (value, label)."""
    figure = go.Figure()
    figure.add_scatter(x=df["time_s"], y=df[column], mode="lines", name=column)
    for value, label in lines:
        figure.add_hline(y=value, line_dash="dash", line_color=config.REFERENCE_LINE_COLOR,
                         annotation_text=label)
    figure.update_layout(title=title, height=config.CHART_HEIGHT, margin=config.CHART_MARGIN)
    figure.update_xaxes(title="time [s]")
    figure.update_yaxes(title=unit)
    return figure


def altitude_chart(df: pd.DataFrame, params: Params) -> go.Figure:
    """Altitude above the take-off point, with the fence altitude H and H − m."""
    lines = [(params.fence_height_m, "H"), (params.fence_height_m - params.release_margin_m, "H − m")]
    return time_chart(df, "alt_m", "Altitude", "m", lines)


def distance_chart(df: pd.DataFrame, params: Params) -> go.Figure:
    """Horizontal distance to home, with the fence radius R and the release radius R − m."""
    lines = [(params.fence_radius_m, "R"), (params.fence_radius_m - params.release_margin_m, "R − m")]
    return time_chart(df, "dist_m", "Distance to home", "m", lines)


def speed_chart(df: pd.DataFrame) -> go.Figure:
    """GNSS ground speed."""
    return time_chart(df, "ground_speed_ms", "Ground speed", "m/s", [])


def voltage_chart(df: pd.DataFrame) -> go.Figure:
    """Battery voltage."""
    return time_chart(df, "vbat_v", "Battery voltage", "V", [])


def current_chart(df: pd.DataFrame) -> go.Figure:
    """Battery current."""
    return time_chart(df, "current_a", "Current", "A", [])


def mah_chart(df: pd.DataFrame, params: Params) -> go.Figure:
    """Consumed charge and the battery-RTH threshold T(d); the battery RTH is due where they meet."""
    figure = time_chart(df, "mah_drawn", "Consumed charge and threshold T(d)", "mAh", [])
    threshold = metrics.battery_threshold(params, df["dist_m"])
    figure.add_scatter(x=df["time_s"], y=threshold, mode="lines", name="T(d)")
    return figure
