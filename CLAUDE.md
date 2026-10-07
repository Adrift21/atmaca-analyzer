# ATMACA Flight Analyzer – project brief for Claude Code

## 1. Communication
- Talk to the user (Kaan, "Adrift") in **Turkish**. Code, identifiers, comments, commit messages, UI text, README and
  ARCHITECTURE are in **English**. `docs/MODIFICATION_GUIDE.md` is in **Turkish** (it is the team's rehearsal sheet).
- Work in the build order of Section 14. After every step: run the tests, start the app, give a short demo list
  (what to click, what to see), report the line count per file, commit, and **stop**. Never start the next step on
  your own.

## 2. Why this program exists
ATMACA is a graduation project (Işık University, COMP4902, Group 20): a GPS-assisted, safety-focused 6-inch FPV
drone running **INAV 9.1**, plus a ground-side program that analyses the drone's blackbox flight logs.

A large ground station (ABP Framework, users, database, parameter sets, script generation) already exists in another
repository. **This repository is a different, deliberately small program.** In the final presentation every team
member (Kaan, Umut, Ali) must be able to explain *any* part of the code, and the jury will ask for live
**modifications** ("change this threshold", "add this chart", "show this value") that the team makes by hand,
probably without AI help. Therefore:

> **The most important requirement of this project is that the code is small, flat and obvious.**
> When a feature and simplicity conflict, simplicity wins. Ask before adding anything that is not in this file.

Do not copy code or architecture from the ABP ground station.

## 3. What the program does (user view)
One web page, run locally on a laptop with `streamlit run app.py`:

1. In the sidebar the user picks a flight log from the `logs/` folder (or uploads one, which is saved into `logs/`)
   and, if the file contains several flights, picks the flight.
2. The sidebar also shows the **safety parameters that were loaded on the drone** for that flight (fence radius R,
   fence altitude H, release margin m, confirmation time, battery capacity C, landing reserve r, landing allowance
   L, return cost k, warning time). They start with the defaults of `config.py` and can be changed ("what if R had
   been 40 m?"); the analysis is recomputed immediately.
3. The page then shows, from top to bottom:
   - **Summary cards:** flight time, max distance from home, max altitude, mAh used, remaining capacity %,
     minimum voltage, minimum satellite count.
   - **Time slider** (cursor): moves a marker on the map and a vertical line on every chart.
   - **Map** (left) with the flight path coloured by flight mode, home, touchdown point, the fence circle R, the
     release circle R − m and the event markers; **success-criteria table** (right) with value, limit and
     PASS / FAIL / N/A.
   - **Charts** (two columns): altitude, distance to home, ground speed, voltage, current, and consumed mAh
     together with the battery-RTH threshold T(d).
   - **Events table:** time, event, detail.
   - **Expander "Data"**: first rows of the normalized data, and the list of expected columns that were found or
     missing in the file (helps when a real log does not load).

```
+-- sidebar --------+  ATMACA Flight Analyzer – <file> · flight 1
| Log file  [v]     |  [time 7:05] [max dist 51 m] [max alt 12 m] [1240 mAh] [59 %] [21.9 V] [12 sats]
| Upload [..]       |  time ----o--------------------------------------------
| Flight    [v]     |  +------------ map ------------+  +-- success criteria ---------+
| --- parameters -- |  | path by mode, home, fence   |  | SC-2 drift RMS 1.2 ≤1.5 PASS|
| R  [50] H [30]    |  | circles, events, cursor     |  | SC-6 response 0.7 ≤1.0 PASS |
| m  [15] confirm 1 |  +-----------------------------+  +-----------------------------+
| C [3000] r [0.20] |  [altitude      ] [distance to home]
| L [150]  k [0.9]  |  [ground speed  ] [voltage         ]
| warning [5]       |  [current       ] [mAh vs T(d)     ]
+-------------------+  events table · ▸ Data
```

## 4. Non-goals (do NOT build these)
No login, users or roles. No database or ORM (files only). No parameter-set management or INAV script generation.
No test-session management. No comparison of flights. No PDF/CSV export (the drills in Section 15 may add a small
download button later). No multipage app, no REST API, no background jobs, no async, no Docker, no classes with
inheritance, no dependency injection, no plugin systems, no custom Streamlit components, no JavaScript.

## 5. Simplicity rules (apply to every line)
1. **One concept per file**; the file name says what is inside. Each file starts with a docstring of 2–4 lines:
   what the file does and what someone would typically change here.
2. **Every number, name, colour and threshold lives in `config.py`.** No magic numbers elsewhere.
3. **`app.py` contains only layout:** it calls functions and displays the results. No calculations in `app.py`.
4. Only `app.py` imports Streamlit. All other modules are plain Python functions that can be tested with pytest.
5. **Plain functions.** The only classes are the three small dataclasses in `models.py`. No inheritance, no
   decorators except `@st.cache_data` on the cached loading function in `app.py`.
6. Functions ≤ 40 lines, nesting ≤ 3 levels, descriptive names, type hints, a one-line docstring.
7. Prefer explicit, readable code over clever code: intermediate variables with names, simple `for` loops are fine
   (a flight has only ~6,000 samples at 10 Hz). No long pandas method chains, no one-line comprehensions that do
   two things, no regular expressions unless unavoidable, no `lambda` stored in variables.
8. **Extensible by registration:** each chart, event detector and metric is one function; adding one means writing
   one function and adding one line (Section 15 lists the drills that must stay this easy).
9. Size budget (excluding tests): `app.py` ≤ 200 lines, every other module ≤ 220 lines, **total ≤ 1,000 lines**.
   Report the line counts after every step. If a budget is exceeded, simplify before continuing.
10. Few dependencies: `streamlit`, `pandas`, `plotly`, and `pytest` for tests. Nothing else without asking.

## 6. Tech stack and running
- Python 3.12 (or newer) in a virtual environment; pin the installed versions in `requirements.txt`.
- Streamlit for the page, pandas for the data, **Plotly** for both charts and the map (one library to learn).
  Map: `plotly.express.scatter_map` / `go.Scattermap` with `map_style="open-street-map"` (no token needed). If the
  installed Plotly is older and lacks these, use the `scatter_mapbox` equivalents with the same style.
- `.streamlit/config.toml`: `[browser] gatherUsageStats = false`; wide layout is set in `app.py`.
- Windows is the main platform (PowerShell); keep paths with `pathlib`.

```powershell
py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
pytest
```

## 7. Project structure
```
atmaca-analyzer/
  CLAUDE.md              this file
  README.md              how to install, run, decode logs, run tests (English)
  requirements.txt
  .streamlit/config.toml
  app.py                 the page (layout only)
  config.py              all constants: defaults, thresholds, column map, mode rules, colours, paths
  models.py              dataclasses Params, Event, Metric
  loader.py              file -> normalized 10 Hz DataFrame (+ decoding INAV logs)
  geo.py                 distances in metres and circle points for the map
  events.py              DataFrame -> list[Event]
  metrics.py             DataFrame + events + Params -> list[Metric]
  charts.py              Plotly figures: the map and the time-series charts
  samples/               synthetic flights (*.csv) with ground truth (*.truth.json) – provided, do not edit
  tools/synthlog.py      generator of the samples – provided
  tools/bin/             blackbox_decode.exe goes here (not committed)
  logs/                  the user's real logs (.TXT/.BBL); logs/decoded/ holds decoder output (not committed)
  tests/                 test_loader.py, test_events.py, test_metrics.py, fixtures/
  docs/ARCHITECTURE.md   data flow, modules, data model (input for the RAD)
  docs/MODIFICATION_GUIDE.md   drills for the presentation (Turkish)
```
`.gitignore`: `.venv/`, `__pycache__/`, `logs/decoded/`, `tools/bin/`, `*.pyc`. Real logs in `logs/` are committed only
if the user says so.

Data flow (keep it exactly this simple):
```
file --loader--> DataFrame (10 Hz, normalized) --events--> list[Event] --metrics--> list[Metric]
                        \___________________________charts_____________________________/--> app.py
```

## 8. Data model
### 8.1 Normalized DataFrame (one row every 0.1 s, one flight)
The column names are the ones of the synthetic samples (`tools/synthlog.py → COLUMNS`), so the samples load
without any renaming:

| Column | Unit / values | Meaning |
|---|---|---|
| `time_s` | s | time since arming (first row ≈ 0) |
| `armed` | 0/1 | motors armed |
| `lat`, `lon` | degrees | GNSS position |
| `alt_m` | m | altitude above the take-off point |
| `ground_speed_ms` | m/s | GNSS ground speed |
| `vbat_v` | V | battery voltage |
| `current_a` | A | battery current |
| `mah_drawn` | mAh | charge used since arming |
| `flight_mode` | EASY, NORMAL, SPORT, RTH, LAND | ATMACA mode name |
| `rth_reason` | "", PILOT, FENCE, BATTERY, FAILSAFE | why RTH is active (empty if unknown) |
| `failsafe` | 0/1 | INAV failsafe active |
| `rc_link_ok` | 0/1 | valid RC frames received |
| `sticks_centered` | 0/1 | all sticks in their centre band |
| `gps_sats` | count | satellites |

Derived columns added by the loader: `x_m`, `y_m` (east/north of home in metres) and `dist_m` (horizontal distance
to home). Home = `GPS_home` of the log if present, otherwise the first row with a valid fix.

### 8.2 Dataclasses (`models.py`, ~40 lines)
```python
@dataclass
class Params:            # safety parameters loaded on the drone for this flight (entered in the sidebar)
    fence_radius_m: float        # R
    fence_height_m: float        # H
    release_margin_m: float      # m
    confirm_s: float             # breach confirmation time
    capacity_mah: float          # C
    reserve: float               # r (0.20 = 20 %)
    landing_allowance_mah: float # L
    return_cost_mah_per_m: float # k
    warning_s: float             # battery warning time before the RTH

@dataclass
class Event:
    time_s: float
    kind: str            # ARM, DISARM, MODE, RTH_START, LINK_LOST, LINK_RESTORED, FAILSAFE_START,
                         # FAILSAFE_END, FENCE_BREACH, FENCE_RELEASE, ALTITUDE_BREACH
    detail: str = ""     # e.g. the new mode, or the RTH reason
    lat: float | None = None
    lon: float | None = None

@dataclass
class Metric:
    criterion: str       # "SC-2" … or "" for information rows
    name: str            # e.g. "Hover drift RMS"
    value: float | None  # None when not tested in this flight
    unit: str
    limit: str           # readable limit, e.g. "≤ 1.5"
    passed: bool | None  # None = N/A (this flight did not test the criterion)
```

## 9. Loading flights (`loader.py`)
Public functions (keep these names; the tests and the guide use them):
- `list_log_files() -> list[Path]` – files in `samples/` and `logs/` with extensions `.csv`, `.txt`, `.bbl`
  (excluding `logs/decoded/`).
- `save_upload(name: str, data: bytes) -> Path` – writes an uploaded file into `logs/`.
- `flights_in_file(path) -> list[Path]` – a normalized CSV is one flight; a `.TXT`/`.BBL` file is decoded (once)
  and returns one decoded CSV per flight.
- `load_flight(csv_path) -> pd.DataFrame` – reads a normalized or decoder CSV and returns the normalized DataFrame
  with the derived columns.
- `column_report(csv_path) -> list[tuple[str, str, bool]]` – for the "Data" expander: normalized column, source
  column, found?

### 9.1 Normalized CSV (synthetic samples, available today)
Recognised by the column `time_s`. Read with pandas, add the derived columns, done.

### 9.2 INAV blackbox logs (real flights, from the first bench log on)
- Decoder: INAV **blackbox-tools 9.0.0** (`blackbox_decode`, GPL-3.0), the latest release, used for INAV 9.1 logs.
  Windows binary: `blackbox-tools-9.0.0_windows-x86_64.zip` from
  https://github.com/iNavFlight/blackbox-tools/releases/tag/v9.0.0 → `tools/bin/blackbox_decode.exe`. Run it as a
  separate program with `subprocess.run` (never import or copy its code; do not commit the binary). Path and
  arguments come from `config.DECODER_PATH` / `config.DECODER_ARGS`; check the options with `--help` first (merging
  the GPS data into the main CSV is wanted). Output goes to `logs/decoded/<log name>/`; if that folder already has
  CSV files, do not decode again. One blackbox file may contain several flights (one per arming) → one CSV each.
- If the decoder is missing or fails, `app.py` shows a clear message (what to download, where to put it) and the
  rest of the page still works for normalized CSV files.
- **Column mapping lives in `config.COLUMN_MAP`.** The INAV 9.1 blackbox field names are known from
  `src/main/blackbox/blackbox.c` (`time`, `vbat`, `amperage`, `rcData[0..3]`, `navPos[0..2]`, `BaroAlt`, `navState`,
  `flightModeFlags`, `stateFlags`, `failsafePhase`, `rxSignalReceived`, `rxFlightChannelsValid`, `GPS_coord[0..1]`,
  `GPS_numSat`, `GPS_speed`, `GPS_altitude`, `GPS_home[0..1]`), but the decoder adds unit suffixes such as
  `" (us)"`, `" (V)"`, `" (A)"`, `" (flags)"`. Fill `COLUMN_MAP` with the most likely header names, mark the whole
  map with a comment `# UNVERIFIED – check with the first bench log`, and make the loader report missing columns
  instead of crashing. Never invent other field names.
- Conversion rules (each one a small, named function or a few clear lines):
  - `time_s` = (`time` in µs − first value) / 1,000,000.
  - Resample to 10 Hz: keep the first row of every 0.1 s bin (`config.SAMPLE_RATE_HZ`); forward-fill GPS columns
    (they update more slowly than the main frames).
  - `alt_m` = (`navPos[2]` − its first value) / 100; if missing, the same with `BaroAlt` (both in cm).
  - `mah_drawn`: no mAh field exists in INAV blackbox logs → integrate the current:
    `mah += current_a × dt_s / 3.6` (the same formula as `tools/synthlog.py`). Easy to explain, no hidden field.
  - `flight_mode` from the `flightModeFlags` text with `config.MODE_RULES`, an ordered list like
    `[("RTH", "NAV_RTH"), ("EASY", "NAV_POSHOLD"), ("NORMAL", "ANGLE")]`: the first rule whose text appears in the
    flags wins, otherwise `"SPORT"` (acro). Function `mode_from_flags(flags: str) -> str`. The flag names are
    UNVERIFIED as well.
  - `failsafe` = 1 when `failsafePhase` is not idle; `rc_link_ok` = `rxSignalReceived`.
  - `sticks_centered` = 1 when roll, pitch and yaw (`rcData[0..2]`) are within ±`STICK_DEADBAND_US` of
    `STICK_CENTER_US` and the throttle (`rcData[3]`) is within ±`THROTTLE_DEADBAND_US` (ATMACA's Easy mode treats the
    throttle centre as "hold altitude").
  - `armed` = 1 (blackbox logs are written only while armed); `rth_reason` = "" (inferred later, Section 10).
  - Positions: `GPS_coord[0]`/`[1]` (degrees), `ground_speed_ms` from `GPS_speed`, `gps_sats` from `GPS_numSat`.

### 9.3 Geometry (`geo.py`, ~40 lines)
- `to_xy_m(lat, lon, home_lat, home_lon) -> (x, y)`: equirectangular approximation (metres per degree of latitude
  111,320; longitude scaled by cos(home latitude)). Accurate enough within a few kilometres and easy to explain.
- `circle_latlon(home_lat, home_lon, radius_m, points=72) -> (lats, lons)`: points of a circle for the map.

## 10. Events (`events.py`)
`find_events(df, params) -> list[Event]` calls one small detector per event kind and returns all events sorted by
time. Each detector compares a row with the previous row ("the first row where the condition becomes true"):

| Event | Rule |
|---|---|
| ARM / DISARM | first row; the row where `armed` goes 1 → 0 |
| MODE | `flight_mode` differs from the previous row; detail = new mode |
| RTH_START | `flight_mode` becomes RTH; detail = `rth_reason` of that row, or the inferred reason + " (inferred)" |
| LINK_LOST / LINK_RESTORED | `rc_link_ok` 1 → 0 / 0 → 1 |
| FAILSAFE_START / FAILSAFE_END | `failsafe` 0 → 1 / 1 → 0 |
| FENCE_BREACH | `dist_m` > R continuously for `confirm_s`; time = first exceeding row + `confirm_s` |
| FENCE_RELEASE | first change to EASY after an RTH_START with reason FENCE |
| ALTITUDE_BREACH | `alt_m` > H continuously for `confirm_s` (information only) |

RTH reason inference (only when the log has no reason, i.e. real INAV logs), in this order: `failsafe` = 1 →
FAILSAFE; `mah_drawn` ≥ T(d) − `config.BATTERY_REASON_TOLERANCE_MAH` → BATTERY; `dist_m` > R → FENCE; otherwise PILOT.
T(d) = C·(1 − r) − L − k·d (function `battery_threshold(params, dist_m)` in `metrics.py`, also used by the chart).

## 11. Metrics (`metrics.py`)
`compute_metrics(df, events, params) -> list[Metric]` calls the functions below in this order and concatenates
their results. A function returns `passed=None` (N/A) rows when the flight did not test its criterion. All limits
come from `config.py`. The definitions are those of the RAD; `tools/metrics_ref.py` of the old starter kit used the
same definitions, so the values in `samples/*.truth.json` must be reproduced (Section 13).

| Function | Criterion | Definition | Limit |
|---|---|---|---|
| `summary` | – | flight time, max distance, max altitude, mAh used, remaining % = (C − last mAh)/C, min voltage | info |
| `hover_drift` | SC-2 | hover segments = consecutive rows with mode EASY, sticks centred and armed, ≥ `HOVER_MIN_SEGMENT_S` (20 s). Use the **longest** segment; it must last ≥ `SC2_MIN_HOVER_S` (60 s), else N/A. Hold point = position and altitude at the segment start. From start + `HOVER_SETTLE_S` (2 s) to the segment end: horizontal distance to the hold point → RMS and max; altitude difference → RMS. Three rows. | RMS ≤ 1.5 m, max ≤ 3 m, altitude RMS ≤ 1 m |
| `landing_error` | SC-3 | only if the flight has an RTH_START and the last armed row has mode RTH (the RTH landed): `dist_m` of the last armed row | ≤ 3 m |
| `failsafe_response` | SC-4 | first LINK_LOST, first RTH_START with reason FAILSAFE: response = RTH start − link lost. Information rows: link restored (first row after the RTH start with `rc_link_ok` = 1) and control regained (first row after the RTH start whose mode is not RTH or LAND) | ≤ 2 s |
| `battery_rth` | SC-5 | first RTH_START with reason BATTERY; trigger time = RTH start − `warning_s`; take the row nearest to it; threshold T = T(d of that row); error = mAh at trigger − T; remaining = C − mAh of the last row | \|error\| ≤ 50 mAh; remaining ≥ 20 % of C |
| `fence` | SC-6 | first row with `dist_m` > R that stays > R for `confirm_s` (= first exceed); confirmed = first exceed + `confirm_s`; fence RTH = first RTH_START with reason FENCE at or after the first exceed; response = fence RTH − confirmed; release = first change to EASY after the fence RTH; episode = first exceed … release (or end of flight); horizontal overshoot = max `dist_m` in the episode − R; vertical overshoot = max(0, max `alt_m` in the episode − H) | response ≤ 1 s; overshoot ≤ 15 m horizontally, ≤ 5 m vertically |
| `return_cost` | – | k measured in this flight: from the first RTH_START, the RTH rows; climb end = first RTH row with speed > `RETURN_CLIMB_END_SPEED_MS` (1 m/s); descent start = first later row whose altitude is lower than the previous row by more than `DESCENT_STEP_M` (0.05 m); k = (mAh at descent start − mAh at climb end) / `dist_m` at climb end | info (the team copies it into the sidebar default) |
| `endurance` | SC-8 | only if flight time ≥ `SC8_MIN_FLIGHT_S` (600 s), else N/A: no NORMAL or SPORT rows, and remaining ≥ 20 % | both conditions |

Helper functions such as `hover_segments(df)` and `battery_threshold(params, dist_m)` are public so that tests and
charts can use them.

## 12. Page details (`app.py`, `charts.py`)
- `st.set_page_config(page_title="ATMACA Flight Analyzer", layout="wide")`. The loading function in `app.py` is
  wrapped with `@st.cache_data` (keyed by path and modification time) so decoding happens once.
- Charts: one generic helper `time_chart(df, column, title, unit, cursor_s, lines)` where `lines` is a list of
  `(value, label)` horizontal reference lines; every chart function is then 2–4 lines:
  `altitude_chart` (lines H and H − m), `distance_chart` (R and R − m), `speed_chart`, `voltage_chart`,
  `current_chart`, and `mah_chart` (consumed mAh plus a second line T(d) per row, which shows the battery-RTH idea
  at a glance). The cursor is a vertical line at `cursor_s`.
- `map_figure(df, events, params, cursor_s)`: a grey line for the path, points coloured by mode
  (`config.MODE_COLORS`), markers for home and touchdown, the circles R (red) and R − m (orange, dotted), one
  marker per event with hover text, and a marker at the cursor time. Centre on home; choose the zoom from the
  maximum distance with a simple rule in `config`.
- Success-criteria table: a pandas DataFrame built from the `Metric` list with columns Criterion, Metric, Value,
  Limit, Result (PASS / FAIL / N/A); colour the Result column (green / red / grey) with a simple style function.
- Events table: time (s, one decimal), event, detail.
- Map tiles need internet. If there is none, Plotly shows the path on an empty background; mention this in the
  README (`config.MAP_STYLE` can be switched to `"white-bg"`).

### `config.py` contents (grouped, each constant with a one-line comment and its unit)
- Paths: `SAMPLES_DIR`, `LOGS_DIR`, `DECODED_DIR`, `DECODER_PATH`, `DECODER_ARGS`.
- Data: `SAMPLE_RATE_HZ = 10`, `COLUMN_MAP`, `MODE_RULES`, `STICK_CENTER_US = 1500`, `STICK_DEADBAND_US = 30`,
  `THROTTLE_DEADBAND_US = 50`.
- Default safety parameters (`DEFAULT_PARAMS`, shown in the sidebar): R 50 m, H 30 m, m 15 m, confirmation 1.0 s,
  C 3000 mAh, r 0.20, L 150 mAh, k 0.9 mAh/m, warning 5 s.
- Success-criteria limits: `SC2_RMS_MAX_M = 1.5`, `SC2_MAX_M = 3.0`, `SC2_ALT_RMS_MAX_M = 1.0`, `SC2_MIN_HOVER_S = 60`,
  `SC3_LANDING_MAX_M = 3.0`, `SC4_RESPONSE_MAX_S = 2.0`, `SC5_ERROR_MAX_MAH = 50`, `SC5_MIN_REMAINING = 0.20`,
  `SC6_RESPONSE_MAX_S = 1.0`, `SC6_OVERSHOOT_H_MAX_M = 15`, `SC6_OVERSHOOT_V_MAX_M = 5`, `SC8_MIN_FLIGHT_S = 600`,
  `SC8_MIN_REMAINING = 0.20`.
- Analysis rules: `HOVER_MIN_SEGMENT_S = 20`, `HOVER_SETTLE_S = 2`, `RETURN_CLIMB_END_SPEED_MS = 1.0`,
  `DESCENT_STEP_M = 0.05`, `BATTERY_REASON_TOLERANCE_MAH = 20`.
- Look: `MODE_COLORS` (EASY, NORMAL, SPORT, RTH, LAND), `MAP_STYLE = "open-street-map"`, map zoom rule, chart
  height.

Keep the distinction clear in the comments: **parameters** describe what was loaded on the drone (they can differ
per flight and are edited in the sidebar); **limits** are the project's success criteria (fixed in the RAD).

## 13. Tests (`tests/`, pytest)
- `test_metrics.py` must reproduce every value in `samples/*.truth.json` with these parameters and tolerances:
  - hover_before_tuning / hover_after_tuning: exactly one hover segment; drift RMS, drift max and altitude RMS within
    0.05 m.
  - guest_fence (R = 50, H = 30, m = 15, confirm = 1.0): response and release within 0.15 s; horizontal and vertical
    overshoot within 0.15 m.
  - battery_rth (C = 3000, r = 0.20, L = 150, k = 0.9, warning = 5.0): RTH start within 0.15 s; threshold error and
    remaining within 3 mAh; landing error within 0.15 m; return cost k within 0.02 mAh/m.
  - failsafe_rth: response and link restored within 0.15 s; control regained within 0.25 s.
  - N/A cases: e.g. no fence metric values for hover_before_tuning, no landing error for guest_fence.
- `test_events.py`: event times of guest_fence and failsafe_rth (RTH reasons read from the CSV), and the reason
  inference with the `rth_reason` column blanked out.
- `test_loader.py`: a sample loads with all columns and ~10 rows per second; `mode_from_flags` cases; resampling and
  mAh integration on a tiny hand-written decoder-format CSV in `tests/fixtures/` (built from the UNVERIFIED column
  names, replaced by a cut of the first real bench log later).
- Tests use only the public functions, so they also document how to call them.

## 14. Build order (each step: tests green, short demo, line counts, commit, STOP)
1. **Skeleton:** `requirements.txt`, `config.py`, `models.py`, `geo.py`, `loader.py` for normalized CSV only,
   `app.py` with the sidebar file list and the summary cards; `.gitignore`, `.streamlit/config.toml`;
   `test_loader.py`. Demo: open `samples/guest_fence.csv`.
2. **Charts and parameters:** `charts.py` time charts (incl. mAh vs T(d)), sidebar parameter inputs.
3. **Map** with path by mode, home, touchdown, fence circles.
4. **Events:** `events.py`, events table, event markers on the map, `test_events.py`.
5. **Metrics:** `metrics.py`, success-criteria table, `test_metrics.py` (all truth values pass).
6. **Time slider:** cursor marker on the map and vertical line on all charts.
7. **INAV blackbox logs:** decoder call, `COLUMN_MAP`, `mode_from_flags`, resampling, mAh integration, flight
   selection for multi-flight files, upload into `logs/`, "Data" expander with the column report, decoder-missing
   message, fixture-based tests. (When the first real bench log exists, the mapping is verified and corrected.)
8. **Documentation and simplicity review:** README, `docs/ARCHITECTURE.md`, `docs/MODIFICATION_GUIDE.md` (Section
   15), final line counts; re-read every file against Section 5 and simplify where a student could stumble.

## 15. Modification drills (must stay easy; document them in `docs/MODIFICATION_GUIDE.md`)
The jury will ask for changes like these. After step 8, every drill must be doable in **≤ 10 changed lines in at
most 2 files**. For each drill the guide (Turkish) gives: the request, the file and function, the exact change (a
short diff), and how to see the result on the page.

1. Change a success limit (e.g. SC-2 RMS 1.5 → 1.0 m).
2. Change a default parameter (e.g. fence radius 50 → 40 m).
3. Add a chart (e.g. satellite count over time).
4. Show ground speed in km/h instead of m/s.
5. Add a summary card (e.g. maximum ground speed).
6. Add an event (e.g. "LOW_SATS" when satellites drop below 8).
7. Add a metric with a limit (e.g. maximum climb rate ≤ 3 m/s).
8. Change the colour of a flight mode on the map.
9. Hide or show the release circle on the map.
10. Add a download button for the success-criteria table as CSV.
11. Analyse only a time range of the flight (two-handle slider that slices the DataFrame).
12. Change the hover-segment rule (minimum 20 → 30 s, or a wider stick deadband).
13. Add a column to the events table (distance from home at the event).
14. Rename or translate labels on the page.
15. Show a warning banner when the voltage falls below a limit.

The guide also contains a one-page "how the program works" explanation (data flow, the role of each file, what
happens when the user moves the slider) so that every team member can present any part.

## 16. Documentation for the report
`docs/ARCHITECTURE.md` (English) is the input for the new RAD: purpose, data flow diagram (Mermaid), module table
(file, responsibility, public functions), the three dataclasses and the normalized columns (a class diagram in
Mermaid), the event and metric definitions (link to Sections 10–11 of this file), external interfaces
(blackbox_decode, OpenStreetMap tiles), and the test approach.

## 17. Open items (ask the user or resolve later)
- Real decoder column names and flight-mode flag names → verify `COLUMN_MAP` and `MODE_RULES` with the first bench
  log (expected after the drone is assembled, end of October 2026).
- Whether `blackbox_decode` 9.0.0 decodes INAV 9.1 logs without errors (check with the first bench log).
- Real RTH reasons cannot be read from the log; they are inferred (Section 10) and marked "(inferred)".
