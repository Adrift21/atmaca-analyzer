"""The web page: the file choice in the sidebar and the flight summary (layout only, no calculations).

Typical changes: labels, the order of the page sections, which results are shown.
Run with:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import config
import loader
import metrics

st.set_page_config(page_title="ATMACA Flight Analyzer", layout="wide")


@st.cache_data
def load_flight_cached(path_text: str, modified_time: float) -> pd.DataFrame:
    """Load a flight once; the modification time is part of the cache key, so a changed file is read again."""
    return loader.load_flight(Path(path_text))


def file_label(path: Path) -> str:
    """Show a file as 'folder/name' in the sidebar."""
    return f"{path.parent.name}/{path.name}"


# ---------------------------------------------------------------- sidebar
files = loader.list_log_files()
if not files:
    st.warning(f"No flight files found in {config.SAMPLES_DIR} or {config.LOGS_DIR}.")
    st.stop()
path = st.sidebar.selectbox("Log file", files, format_func=file_label)
params = config.DEFAULT_PARAMS

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
