"""The web page: file choice and safety parameters in the sidebar, then summary cards and charts.

Layout only, no calculations. Typical changes: labels, the order of the sections, which charts are shown.
Run with:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import config
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
left, right = st.sidebar.columns(2)
params = Params(
    fence_radius_m=left.number_input("R radius [m]", value=defaults.fence_radius_m),
    fence_height_m=right.number_input("H height [m]", value=defaults.fence_height_m),
    release_margin_m=left.number_input("m margin [m]", value=defaults.release_margin_m),
    confirm_s=right.number_input("Confirm [s]", value=defaults.confirm_s),
    capacity_mah=left.number_input("C capacity [mAh]", value=defaults.capacity_mah),
    reserve=right.number_input("r reserve [0–1]", value=defaults.reserve),
    landing_allowance_mah=left.number_input("L landing [mAh]", value=defaults.landing_allowance_mah),
    return_cost_mah_per_m=right.number_input("k return [mAh/m]", value=defaults.return_cost_mah_per_m),
    warning_s=left.number_input("Warning [s]", value=defaults.warning_s),
)

try:
    df = load_flight_cached(str(path), path.stat().st_mtime)
except ValueError as error:
    st.error(f"Could not load {path.name}: {error}")
    st.stop()

# ---------------------------------------------------------------- page
st.title(f"ATMACA Flight Analyzer – {path.name}")

cards = metrics.summary(df, params)
for column, card in zip(st.columns(len(cards)), cards):
    column.metric(card.name, f"{card.value} {card.unit}")

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
