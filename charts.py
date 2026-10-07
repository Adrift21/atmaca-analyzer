"""Plotly figures of the page: the map and the time-series charts below it.

Typical changes: add a chart (one small function here, one line in app.py), change a title, unit or limit line,
or add something to the map. Colours and sizes are in config.py.
"""
import pandas as pd
import plotly.graph_objects as go

import config
import geo
import loader
import metrics
from models import Params


# ---------------------------------------------------------------- map
def map_zoom(max_dist_m: float) -> int:
    """Zoom level of the map: the first step of config.MAP_ZOOM_RULE that covers the flight."""
    for distance_m, zoom in config.MAP_ZOOM_RULE:
        if max_dist_m <= distance_m:
            return zoom
    return config.MAP_ZOOM_FAR


def add_points(figure: go.Figure, lats: list | pd.Series, lons: list | pd.Series,
               name: str, color: str, size: int) -> None:
    """Add a group of round markers to the map (one entry in the legend)."""
    figure.add_scattermap(lat=lats, lon=lons, mode="markers", name=name, marker={"color": color, "size": size})


def map_figure(df: pd.DataFrame, params: Params) -> go.Figure:
    """Map: path coloured by flight mode, home, touchdown, fence circle R and release circle R − m."""
    home_lat, home_lon = loader.find_home(df)
    figure = go.Figure()
    figure.add_scattermap(lat=df["lat"], lon=df["lon"], mode="lines", name="path", line={"color": config.PATH_COLOR})
    for mode, color in config.MODE_COLORS.items():
        rows = df[df["flight_mode"] == mode]
        if len(rows) > 0:                                              # only modes flown appear in the legend
            add_points(figure, rows["lat"], rows["lon"], mode, color, config.MAP_POINT_SIZE)

    fence_lats, fence_lons = geo.circle_latlon(home_lat, home_lon, params.fence_radius_m)
    figure.add_scattermap(lat=fence_lats, lon=fence_lons, mode="lines", name="fence R",
                          line={"color": config.FENCE_COLOR})
    release_m = params.fence_radius_m - params.release_margin_m
    release_lats, release_lons = geo.circle_latlon(home_lat, home_lon, release_m)
    add_points(figure, release_lats, release_lons, "release R − m", config.RELEASE_COLOR, config.MAP_POINT_SIZE)

    touchdown = metrics.last_armed_row(df)
    add_points(figure, [home_lat], [home_lon], "home", config.HOME_COLOR, config.MAP_MARKER_SIZE)
    add_points(figure, [touchdown["lat"]], [touchdown["lon"]], "touchdown", config.TOUCHDOWN_COLOR,
               config.MAP_MARKER_SIZE)

    max_dist_m = max(df["dist_m"].max(), params.fence_radius_m)      # the fence circle must be visible too
    center = {"lat": home_lat, "lon": home_lon}
    figure.update_layout(map={"style": config.MAP_STYLE, "center": center, "zoom": map_zoom(max_dist_m)},
                         height=config.MAP_HEIGHT, margin=config.MAP_MARGIN)
    return figure


# ---------------------------------------------------------------- time charts


def time_chart(df: pd.DataFrame, column: str, title: str, unit: str,
               lines: list[tuple[float, str]]) -> go.Figure:
    """Line chart of one column over time, with horizontal reference lines given as (value, label)."""
    figure = go.Figure()
    figure.add_scatter(x=df["time_s"], y=df[column], mode="lines", name=column)
    for number, (value, label) in enumerate(lines):
        position = "top right" if number == 0 else "bottom right"   # labels of close lines must not overlap
        figure.add_hline(y=value, line_dash="dash", line_color=config.REFERENCE_LINE_COLOR,
                         annotation_text=label, annotation_position=position)
    figure.update_layout(title=title, height=config.CHART_HEIGHT, margin=config.CHART_MARGIN)
    figure.update_xaxes(title="time [s]")
    figure.update_yaxes(title=unit)
    return figure


def altitude_chart(df: pd.DataFrame, params: Params) -> go.Figure:
    """Altitude above the take-off point, with the fence height H and the release height H − m."""
    fence_m = params.fence_height_m
    release_m = params.fence_height_m - params.release_margin_m
    lines = [(fence_m, f"fence H = {fence_m:g} m"), (release_m, f"release H − m = {release_m:g} m")]
    return time_chart(df, "alt_m", "Altitude", "m", lines)


def distance_chart(df: pd.DataFrame, params: Params) -> go.Figure:
    """Horizontal distance to home, with the fence radius R and the release radius R − m."""
    fence_m = params.fence_radius_m
    release_m = params.fence_radius_m - params.release_margin_m
    lines = [(fence_m, f"fence R = {fence_m:g} m"), (release_m, f"release R − m = {release_m:g} m")]
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
