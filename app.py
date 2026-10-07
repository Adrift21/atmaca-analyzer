"""The web page: file and safety parameters in the sidebar; cards, map, success criteria, charts and events.

Layout only, no calculations. Typical changes: labels, the order of the sections, which charts are shown.
Run with:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import config
import events
import loader
import metrics
from models import Params

st.set_page_config(page_title="ATMACA Flight Analyzer", layout="wide")


@st.cache_data
def load_flight_cached(path_text: str, modified_time: float) -> pd.DataFrame:
    """Load a flight once; the modification time is part of the cache key, so a changed file is read again."""
    return loader.load_flight(Path(path_text))


def file_label(path: Path) -> str:
    """Show a file as 'folder/name' in the sidebar."""
    return f"{path.parent.name}/{path.name}"


# ---------------------------------------------------------------- sidebar: file
files = loader.list_log_files()
if not files:
    st.warning(f"No flight files found in {config.SAMPLES_DIR} or {config.LOGS_DIR}.")
    st.stop()
path = st.sidebar.selectbox("Log file", files, format_func=file_label)

# ---------------------------------------------------------------- sidebar: parameters loaded on the drone
st.sidebar.subheader("Parameters on the drone")
defaults = config.DEFAULT_PARAMS
params = Params(
    fence_radius_m=st.sidebar.number_input("R – fence radius [m]", value=defaults.fence_radius_m),
    fence_height_m=st.sidebar.number_input("H – fence height [m]", value=defaults.fence_height_m),
    release_margin_m=st.sidebar.number_input("m – release margin [m]", value=defaults.release_margin_m),
    confirm_s=st.sidebar.number_input("Breach confirmation time [s]", value=defaults.confirm_s),
    capacity_mah=st.sidebar.number_input("C – battery capacity [mAh]", value=defaults.capacity_mah),
    reserve=st.sidebar.number_input("r – landing reserve (0.20 = 20 %)", value=defaults.reserve),
    landing_allowance_mah=st.sidebar.number_input("L – landing allowance [mAh]",
                                                  value=defaults.landing_allowance_mah),
    return_cost_mah_per_m=st.sidebar.number_input("k – return cost [mAh/m]",
                                                  value=defaults.return_cost_mah_per_m),
    warning_s=st.sidebar.number_input("Battery warning time [s]", value=defaults.warning_s),
)

try:
    df = load_flight_cached(str(path), path.stat().st_mtime)
except ValueError as error:
    st.error(f"Could not load {path.name}: {error}")
    st.stop()
flight_events = events.find_events(df, params)
flight_metrics = metrics.compute_metrics(df, flight_events, params)

# ---------------------------------------------------------------- page
st.title(f"ATMACA Flight Analyzer – {path.name}")

cards = metrics.summary(df, params)
for column, card in zip(st.columns(len(cards)), cards):
    column.metric(f"{card.name} [{card.unit}]", card.value)

map_column, table_column = st.columns([3, 2])
map_column.plotly_chart(charts.map_figure(df, flight_events, params))
criteria = charts.criteria_table(flight_metrics)
table_column.dataframe(criteria.style.map(charts.result_style, subset=["Result"]), hide_index=True,
                       height="content")

figures = [
    charts.altitude_chart(df, params),
    charts.distance_chart(df, params),
    charts.speed_chart(df),
    charts.voltage_chart(df),
    charts.current_chart(df),
    charts.mah_chart(df, params),
]
chart_columns = st.columns(2)
for index, figure in enumerate(figures):
    chart_columns[index % 2].plotly_chart(figure)     # even index: left column, odd index: right column

st.subheader("Events")
st.dataframe(charts.events_table(flight_events), hide_index=True, height="content")
