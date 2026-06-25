#!/usr/bin/env python3
"""
Extract hourly PM2.5 concentrations for every CAMS air-quality monitor in
Bangladesh from the World Bank / DoE CAMS Excel workbooks (2012-2024).

Each workbook has one worksheet per monitoring station, but the sheet names,
column layouts, and header rows differ between years. This script reconciles
those differences and produces a single tidy long-format table:

    station, latitude, longitude, datetime, pm25

Usage:
    python extract_cams_pm25.py
"""

from pathlib import Path
from datetime import datetime, date, timedelta
import re
import numpy as np
import pandas as pd
import python_calamine

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path("/Users/akawano/Library/CloudStorage/GoogleDrive-akawano@stanford.edu/"
                "My Drive/MyProjects/04_brick_kiln_emissions/"
                "PM 2.5 of All CAMS_2012-2024")
COORDS_CSV = DATA_DIR / "WB Report CAMS Coordinates_mod_20251202.csv"

EXCEL_FILES = [
    "Air Quality Data All CAMS_2012-2021.xlsx",
    "Air Quality Data All CAMS_ 2022.xlsx",
    "Air Quality Data All CAMS_2023.xlsx",
    "Air Quality Data All CAMS_2024.xlsx",
]

# ---------------------------------------------------------------------------
# Map every sheet-name spelling variant -> canonical station name
# (canonical names match the coordinates CSV / DoE list)
# ---------------------------------------------------------------------------
STATION_ALIASES = {
    "sangsad": "DoE",            # Jatiya Sangsad Bhaban site = DoE HQ (CAMS-1)
    "doe": "DoE",
    "barc": "BARC",
    "darussalam": "Darussalam",
    "darrussalam": "Darussalam",
    "gazipur": "Gazipur",
    "narayanganj": "Narayanganj",
    "narayonganj": "Narayanganj",
    "narayangonj": "Narayanganj",
    "tv sation": "TV Sation",
    "tv center": "TV Sation",
    "tv st-chittagong": "TV Sation",
    "cda": "CDA",
    "agrabad chittagong": "CDA",
    "khulna": "Khulna",
    "rajshahi": "Rajshahi",
    "rajshahai": "Rajshahi",
    "sylhet": "Sylhet",
    "barishal": "Barishal",
    "mymensing": "Mymensing",
    "mymansingh": "Mymensing",
    "rangpur": "Rangpur",
    "savar": "Savar",
    "narsingdi": "Narsingdi",
    "cumilla": "Cumilla",
}


def canonical_station(sheet_name: str) -> str:
    key = sheet_name.strip().lower()
    if key in STATION_ALIASES:
        return STATION_ALIASES[key]
    raise KeyError(f"Unrecognized sheet/station name: {sheet_name!r}")


# ---------------------------------------------------------------------------
# Per-sheet parsing
# ---------------------------------------------------------------------------
def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _as_datetime(x):
    """Calamine returns native date/datetime; fall back to parsing strings."""
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day)
    if isinstance(x, str) and x.strip():
        try:
            return datetime.fromisoformat(x.strip())
        except ValueError:
            return None
    return None


def parse_sheet(rows) -> pd.DataFrame:
    """Return DataFrame[datetime, pm25] from one raw worksheet (list of rows).

    Two layouts occur:
      A) 3 columns: 'Date', 'Time', 'PM2.5'   (2012-2021 workbook)
      B) 2 columns: '<Average/datetime>', '<PM25 / PM2_5_x>'  (2022-2024)
         - some sheets carry a units row ('ug/m3') just under the header.
    """
    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    dts, pms = [], []

    # ---- Layout A: separate Date + Time columns ----
    if "date" in header and "time" in header:
        di, ti = header.index("date"), header.index("time")
        pi = 2 if len(header) > 2 else len(header) - 1
        for r in rows[1:]:
            if di >= len(r):
                continue
            d = _as_datetime(r[di])
            if d is None:
                continue
            tcell = str(r[ti]) if ti < len(r) and r[ti] is not None else ""
            m = re.search(r"(\d{1,2})", tcell)   # hour from "01:00".."24:00"
            if not m:
                continue
            v = _to_float(r[pi] if pi < len(r) else None)
            if np.isnan(v):
                continue
            dts.append(d + timedelta(hours=int(m.group(1))))
            pms.append(v)

    # ---- Layout B: single datetime column + a PM column ----
    else:
        for r in rows[1:]:
            if not r:
                continue
            d = _as_datetime(r[0])
            if d is None:
                continue
            v = _to_float(r[1] if len(r) > 1 else None)   # 'ug/m3' row -> NaN
            if np.isnan(v):
                continue
            dts.append(d)
            pms.append(v)

    return pd.DataFrame({"datetime": dts, "pm25": pms})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    coords = pd.read_csv(COORDS_CSV).rename(
        columns={"DoE list": "station", "Latitude": "latitude",
                 "Longitude": "longitude"})
    coords = coords[["station", "latitude", "longitude"]]

    frames = []
    for fname in EXCEL_FILES:
        wb = python_calamine.CalamineWorkbook.from_path(str(DATA_DIR / fname))
        for sheet in wb.sheet_names:
            rows = wb.get_sheet_by_name(sheet).to_python()
            if len(rows) < 2:
                continue
            try:
                station = canonical_station(sheet)
            except KeyError as e:
                print("  !! skipped:", e)
                continue
            tidy = parse_sheet(rows)
            tidy.insert(0, "station", station)
            tidy["source_file"] = fname
            frames.append(tidy)
            print(f"  {fname:<42} {sheet:<20} -> {station:<12} "
                  f"{len(tidy):>7,} rows")

    data = pd.concat(frames, ignore_index=True)

    # de-duplicate (a few timestamps overlap across workbooks); keep last
    data = (data.sort_values(["station", "datetime"])
                .drop_duplicates(["station", "datetime"], keep="last"))

    # attach coordinates
    data = data.merge(coords, on="station", how="left")
    data = data[["station", "latitude", "longitude",
                 "datetime", "pm25", "source_file"]]

    out_csv = DATA_DIR / "cams_pm25_hourly_all_monitors_2012-2024.csv"
    data.to_csv(out_csv, index=False)
    print(f"\nWrote {len(data):,} rows -> {out_csv.name}")

    # ---- per-station summary ----
    summary = (data.groupby("station")
               .agg(n_obs=("pm25", "size"),
                    start=("datetime", "min"),
                    end=("datetime", "max"),
                    mean_pm25=("pm25", "mean"),
                    max_pm25=("pm25", "max"))
               .round(1)
               .reindex(coords["station"]))
    summary_csv = DATA_DIR / "cams_pm25_station_summary.csv"
    summary.to_csv(summary_csv)
    print(f"Wrote station summary -> {summary_csv.name}\n")
    print(summary.to_string())


if __name__ == "__main__":
    main()
