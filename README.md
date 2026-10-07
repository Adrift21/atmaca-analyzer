# ATMACA Flight Analyzer

A small local web page that analyses the blackbox flight logs of **ATMACA**, a GPS-assisted, safety-focused 6-inch
FPV drone running INAV 9.1 (Işık University, COMP4902, Group 20). It shows the flight on a map, plots the main
signals over time, lists the events of the flight (mode changes, RTH, link loss, fence breaches …) and checks the
project's success criteria SC-2 … SC-8.

The code is deliberately small and flat so that every team member can explain and change any part of it:
see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it is built and
[docs/MODIFICATION_GUIDE.md](docs/MODIFICATION_GUIDE.md) (Turkish) for step-by-step change exercises.

## Install (Windows, PowerShell)

Python 3.12 or newer is needed (developed with Python 3.14).

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

The page opens in the browser at http://localhost:8501. Pick a file in the sidebar; the five files in `samples/`
are synthetic flights with known results and work without a drone.

## Analysing a real INAV blackbox log

1. Download `blackbox-tools-9.0.0_windows-x86_64.zip` from
   https://github.com/iNavFlight/blackbox-tools/releases/tag/v9.0.0 and copy `bin/blackbox_decode.exe` to
   `tools/bin/blackbox_decode.exe` (the decoder is GPL-3.0 and is not part of this repository).
2. Put the log (`.TXT` or `.BBL`) into `logs/`, or upload it in the sidebar (it is saved into `logs/`).
3. Select it. The first time, it is decoded into `logs/decoded/<log name>/`, one CSV per flight (one flight per
   arming); if the file has several flights, a **Flight** box appears in the sidebar. To decode again, delete that
   folder.

The decoder's column names and INAV's flight-mode flag names are **not yet verified with a real ATMACA log**
(marked `UNVERIFIED` in `config.py`). If a log does not load, open the **Data** section at the bottom of the page:
it lists every expected column and whether it was found. Fix the header names in `config.COLUMN_MAP` (and the
flag names in `config.MODE_RULES`).

INAV does not log the reason for an RTH, so for real logs the reason is inferred and shown as e.g.
`BATTERY (inferred)`.

## Using the page

From top to bottom:

- **Summary cards**: flight time, maximum distance from home, maximum altitude, charge used, charge remaining,
  minimum voltage, minimum satellite count.
- **Time cursor**: moves a green marker on the map and a vertical line on every chart.
- **Map** (left): the flight path coloured by flight mode, home, touchdown point, fence circle R (red), release
  circle R − m (orange dots), one gold marker per event (hover for details) and the time cursor. Click a legend
  entry to hide or show it.
- **Success criteria** (right): value, limit and result of every criterion.
- **Charts**: altitude, distance to home, ground speed, battery voltage, current, and the consumed charge together
  with the battery-RTH threshold T(d).
- **Events**: time, event and detail.
- **Data** (click to open): the first rows of the analysed data and the column report.

The sidebar holds the **safety parameters that were loaded on the drone** for the flight. They start with the
defaults of `config.py`; change them to see "what if" (e.g. "what if R had been 40 m?"). Everything is
recomputed immediately.

### Terms

| Term | Meaning |
|---|---|
| **R** – fence radius | If the drone stays farther than R from home for the confirmation time, the fence starts an RTH. |
| **H** – fence height | Flying higher than H for the confirmation time is reported as an altitude breach. |
| **m** – release margin | The fence RTH gives control back to the pilot (in EASY mode) once the drone is inside **R − m**. |
| **R − m**, **H − m** | The release radius (map, distance chart) and the same margin below H (altitude chart). |
| Breach confirmation time | How long the drone must stay beyond R (or above H) before a breach counts. |
| **C** – battery capacity | Battery capacity in mAh. |
| **r** – landing reserve | Part of C that is never planned for flying (0.20 = 20 %). |
| **L** – landing allowance | Charge needed for the descent and the landing (mAh). |
| **k** – return cost | Charge needed per metre of the way home (mAh/m). The page also measures k in flights with an RTH. |
| **T(d)** | Battery-RTH threshold: T(d) = C·(1 − r) − L − k·d. When the used charge reaches T(d) at distance d from home, the drone must return. |
| Battery warning time | The battery warning starts this long before the battery RTH. |
| Home / touchdown | Take-off point (GPS home of the log, otherwise the first GPS fix) / the last point with the motors armed. |
| Flight modes | **EASY** position hold (GPS assisted), **NORMAL** self-levelling, **SPORT** acro, **RTH** return to home, **LAND**. |
| PASS / FAIL | The flight tested the criterion and met / missed the limit. |
| N/A | This flight did not test the criterion (e.g. no hover of 60 s, no battery RTH). |
| INFO | An information row without a limit (e.g. the time the link came back). |

### Success criteria

| Criterion | What is checked | Limit |
|---|---|---|
| SC-2 | Drift from the hold point in the longest hover (EASY, sticks centred, ≥ 60 s) | RMS ≤ 1.5 m, max ≤ 3 m, altitude RMS ≤ 1 m |
| SC-3 | Distance from home where an RTH landed | ≤ 3 m |
| SC-4 | Time from RC link loss to the failsafe RTH | ≤ 2 s |
| SC-5 | Used charge minus T(d) when the battery warning started; charge left after landing | ± 50 mAh; ≥ 20 % of C |
| SC-6 | Time from a confirmed fence breach to the fence RTH (no fence RTH = FAIL); overshoot beyond R and above H | ≤ 1 s; ≤ 15 m and ≤ 5 m |
| SC-8 | A flight of at least 10 min only in assisted modes (no NORMAL or SPORT), ending with charge left | ≥ 20 % of C |

The limits are in `config.py` (`SC2_…` … `SC8_…`); the exact definitions are in `CLAUDE.md`, sections 10 and 11.

## Tests

```powershell
pytest
```

The tests check that the analysis reproduces the known results in `samples/*.truth.json`, the event detection,
and the conversion of a decoder CSV (`tests/fixtures/decoder_flight.csv`, hand-written until the first real bench
log exists). One test runs the real decoder and is skipped when `tools/bin/blackbox_decode.exe` is missing.

## Without internet

The map tiles come from OpenStreetMap and need internet. Without it, the flight path is drawn on an empty
background; set `MAP_STYLE = "white-bg"` in `config.py` to make that explicit.
