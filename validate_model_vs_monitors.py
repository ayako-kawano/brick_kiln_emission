#!/usr/bin/env python3
"""
Statistical validation of modeled PM2.5 (AELMO/WRF d02 fine-PM surface
concentration) against observed PM2.5 from Bangladesh DoE CAMS monitors.

The model output is provided as a per-station hourly table extracted from the
gridded model field (the *.npy daily maps), one column per CAMS station.
Observations come from the consolidated CAMS hourly file produced by
`extract_cams_pm25.py`.

The script pairs model and observation in space (station) and time (hour),
then computes the standard suite of air-quality model-evaluation statistics
(Emery et al. 2017; Boylan & Russell 2006) at several aggregations:

    * overall (pooled across all stations)
    * per station
    * per calendar month and meteorological season
    * by hour of day (diurnal)

and at hourly, daily-mean, and monthly-mean temporal resolution.

Outputs (written to OUT_DIR):
    metrics_overall.csv          one row per temporal resolution
    metrics_by_station.csv       per-station, hourly + daily
    metrics_by_month.csv         per calendar month
    metrics_by_season.csv        per season
    metrics_diurnal.csv          per hour-of-day
    paired_hourly.csv            tidy paired data (station,datetime,obs,model)
    plots/*.png                  diagnostic figures
    VALIDATION_REPORT.md         written separately by the caller

Usage:
    python validate_model_vs_monitors.py
"""

from pathlib import Path
import os
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths  (edit these if the project is moved)
# ---------------------------------------------------------------------------
PROJ = Path("/Users/akawano/Library/CloudStorage/GoogleDrive-akawano@stanford.edu/"
            "My Drive/MyProjects/04_brick_kiln_emissions")
MODEL_PARQUET = (PROJ / "map_data" /
                 "Brick_Kiln_Health_ERA5_GHRSST_d02_stdat_AELMO_Fine_rev.parquet")
OBS_CSV = (PROJ / "PM 2.5 of All CAMS_2012-2024" /
           "cams_pm25_hourly_all_monitors_2012-2024.csv")
COORDS_CSV = (PROJ / "PM 2.5 of All CAMS_2012-2024" /
              "WB Report CAMS Coordinates_mod_20251202.csv")
# Output dir can be overridden with VAL_OUT (e.g. fast local disk) and copied
# to the project folder afterwards.
OUT_DIR = Path(os.environ.get(
    "VAL_OUT", PROJ / "map_data" / "model_validation"))
PLOT_DIR = OUT_DIR / "plots"

# Map model column names -> canonical station names used in the obs file
MODEL_TO_OBS = {"TV Station": "TV Sation"}

SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
def compute_metrics(obs, mod):
    """Return dict of evaluation statistics for paired arrays obs, mod."""
    obs = np.asarray(obs, dtype=float)
    mod = np.asarray(mod, dtype=float)
    ok = np.isfinite(obs) & np.isfinite(mod)
    obs, mod = obs[ok], mod[ok]
    n = obs.size
    if n < 3:
        return {"n": n}

    diff = mod - obs
    obar, mbar = obs.mean(), mod.mean()
    mb = diff.mean()                                   # Mean Bias
    mae = np.abs(diff).mean()                          # Mean Abs Error
    rmse = np.sqrt((diff ** 2).mean())                 # RMSE
    nmb = diff.sum() / obs.sum() * 100                 # Normalized Mean Bias %
    nme = np.abs(diff).sum() / obs.sum() * 100         # Normalized Mean Err %

    denom = mod + obs
    valid = denom != 0
    mfb = np.mean(2 * diff[valid] / denom[valid]) * 100      # Mean Frac Bias %
    mfe = np.mean(2 * np.abs(diff[valid]) / denom[valid]) * 100  # Mean Frac Err

    # Pearson correlation / R^2
    if obs.std() > 0 and mod.std() > 0:
        r = np.corrcoef(obs, mod)[0, 1]
    else:
        r = np.nan
    r2 = r ** 2 if np.isfinite(r) else np.nan

    # Willmott Index of Agreement
    denom_ioa = np.sum((np.abs(mod - obar) + np.abs(obs - obar)) ** 2)
    ioa = 1 - np.sum(diff ** 2) / denom_ioa if denom_ioa > 0 else np.nan

    # OLS regression model = slope*obs + intercept
    if obs.std() > 0:
        slope, intercept = np.polyfit(obs, mod, 1)
    else:
        slope = intercept = np.nan

    return {
        "n": n, "obs_mean": obar, "mod_mean": mbar,
        "MB": mb, "MAE": mae, "RMSE": rmse,
        "NMB_pct": nmb, "NME_pct": nme, "MFB_pct": mfb, "MFE_pct": mfe,
        "r": r, "R2": r2, "IOA": ioa, "slope": slope, "intercept": intercept,
    }


def benchmark_flag(mfb, mfe):
    """Boylan & Russell (2006) PM performance classification."""
    if not (np.isfinite(mfb) and np.isfinite(mfe)):
        return ""
    if abs(mfb) <= 30 and mfe <= 50:
        return "GOAL"        # best achievable
    if abs(mfb) <= 60 and mfe <= 75:
        return "CRITERIA"    # acceptable
    return "OUTSIDE"


# ---------------------------------------------------------------------------
# Data loading / pairing
# ---------------------------------------------------------------------------
def load_paired():
    model = pd.read_parquet(MODEL_PARQUET)
    model.index = pd.to_datetime(model.index)
    model = model.rename(columns=MODEL_TO_OBS)
    model_long = (model.reset_index()
                  .melt(id_vars=model.index.name or "index",
                        var_name="station", value_name="model"))
    model_long.columns = ["datetime", "station", "model"]

    obs = pd.read_csv(OBS_CSV, usecols=["station", "datetime", "pm25"])
    # timestamps are "%Y-%m-%d %H:%M:%S" with an occasional ".000" suffix
    obs["datetime"] = pd.to_datetime(
        obs["datetime"].str.replace(".000", "", regex=False),
        format="%Y-%m-%d %H:%M:%S", errors="coerce")
    obs = obs.dropna(subset=["datetime"]).rename(columns={"pm25": "obs"})

    # restrict obs to model window and to hourly timestamps
    lo, hi = model.index.min(), model.index.max()
    obs = obs[(obs.datetime >= lo) & (obs.datetime <= hi)]
    obs = obs.groupby(["station", "datetime"], as_index=False)["obs"].mean()

    paired = model_long.merge(obs, on=["station", "datetime"], how="inner")
    paired = paired.dropna(subset=["obs", "model"])
    paired["month"] = paired.datetime.dt.month
    paired["season"] = paired.month.map(SEASONS)
    paired["hour"] = paired.datetime.dt.hour
    paired["date"] = paired.datetime.dt.normalize()
    return paired


def metrics_table(df, group_cols, value_label="hourly"):
    rows = []
    if group_cols is None:
        m = compute_metrics(df.obs, df.model)
        m["benchmark"] = benchmark_flag(m.get("MFB_pct"), m.get("MFE_pct"))
        m["resolution"] = value_label
        rows.append(m)
    else:
        for keys, g in df.groupby(group_cols):
            m = compute_metrics(g.obs, g.model)
            m["benchmark"] = benchmark_flag(m.get("MFB_pct"), m.get("MFE_pct"))
            if not isinstance(keys, tuple):
                keys = (keys,)
            for c, k in zip(group_cols, keys):
                m[c] = k
            rows.append(m)
    out = pd.DataFrame(rows)
    lead = (group_cols or []) + (["resolution"] if group_cols is None else [])
    cols = lead + [c for c in out.columns if c not in lead]
    return out[cols].round(3)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    paired = load_paired()
    paired.to_csv(OUT_DIR / "paired_hourly.csv", index=False)
    print(f"Paired hourly records: {len(paired):,} across "
          f"{paired.station.nunique()} stations")

    # daily and monthly aggregations (mean of both obs & model)
    daily = (paired.groupby(["station", "date"])
             .agg(obs=("obs", "mean"), model=("model", "mean"),
                  month=("month", "first"), season=("season", "first"))
             .reset_index())
    monthly = (paired.assign(ym=paired.datetime.dt.to_period("M"))
               .groupby(["station", "ym"])
               .agg(obs=("obs", "mean"), model=("model", "mean"))
               .reset_index())

    # ---- overall metrics at 3 resolutions ----
    overall = pd.concat([
        metrics_table(paired, None, "hourly"),
        metrics_table(daily, None, "daily"),
        metrics_table(monthly, None, "monthly"),
    ], ignore_index=True)
    overall.to_csv(OUT_DIR / "metrics_overall.csv", index=False)

    # ---- per station (hourly + daily) ----
    st_hourly = metrics_table(paired, ["station"], "hourly")
    st_hourly["resolution"] = "hourly"
    st_daily = metrics_table(daily, ["station"], "daily")
    st_daily["resolution"] = "daily"
    by_station = pd.concat([st_hourly, st_daily], ignore_index=True)
    by_station.to_csv(OUT_DIR / "metrics_by_station.csv", index=False)

    # ---- monthly / seasonal / diurnal ----
    metrics_table(paired, ["month"]).to_csv(
        OUT_DIR / "metrics_by_month.csv", index=False)
    metrics_table(paired, ["season"]).to_csv(
        OUT_DIR / "metrics_by_season.csv", index=False)
    metrics_table(paired, ["hour"]).to_csv(
        OUT_DIR / "metrics_diurnal.csv", index=False)

    print("Wrote metric tables to", OUT_DIR)

    # ---- plots ----
    make_plots(paired, daily, by_station)
    print("Wrote plots to", PLOT_DIR)

    return paired, daily, monthly, overall, by_station


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def make_plots(paired, daily, by_station):
    coords = pd.read_csv(COORDS_CSV).rename(
        columns={"DoE list": "station", "Latitude": "lat", "Longitude": "lon"})

    # 1. Overall hexbin scatter (hourly) with 1:1 line
    fig, ax = plt.subplots(figsize=(6, 6))
    hb = ax.hexbin(paired.obs, paired.model, gridsize=60, mincnt=1,
                   bins="log", cmap="viridis")
    hi = np.nanpercentile(paired[["obs", "model"]].values, 99.5)
    ax.plot([0, hi], [0, hi], "r--", lw=1, label="1:1")
    ax.set_xlim(0, hi); ax.set_ylim(0, hi)
    ax.set_xlabel("Observed PM2.5 (µg/m³)")
    ax.set_ylabel("Model PM2.5 (µg/m³)")
    ax.set_title("Model vs Observed — hourly (all stations)")
    fig.colorbar(hb, label="log10(count)")
    ax.legend()
    fig.tight_layout(); fig.savefig(PLOT_DIR / "scatter_hourly_overall.png", dpi=130)
    plt.close(fig)

    # 2. Per-station daily time series (4x4 grid)
    stations = sorted(paired.station.unique())
    fig, axes = plt.subplots(4, 4, figsize=(20, 12), sharex=True)
    for ax, st in zip(axes.ravel(), stations):
        g = daily[daily.station == st].sort_values("date")
        ax.plot(g.date, g.obs, lw=0.8, label="obs", color="black")
        ax.plot(g.date, g.model, lw=0.8, label="model", color="tab:red", alpha=0.8)
        ax.set_title(st, fontsize=10)
        ax.tick_params(labelsize=7)
    axes.ravel()[0].legend(fontsize=8)
    fig.suptitle("Daily-mean PM2.5: observed vs model", fontsize=14)
    fig.tight_layout(); fig.savefig(PLOT_DIR / "timeseries_daily_by_station.png", dpi=120)
    plt.close(fig)

    # 3. Per-station NMB & R (daily) bar charts
    sd = by_station[by_station.resolution == "daily"].set_index("station").reindex(stations)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 5))
    a1.bar(stations, sd.NMB_pct, color=np.where(sd.NMB_pct >= 0, "tab:red", "tab:blue"))
    a1.axhline(0, color="k", lw=0.8); a1.axhline(30, ls=":", color="grey")
    a1.axhline(-30, ls=":", color="grey")
    a1.set_ylabel("NMB (%)"); a1.set_title("Normalized Mean Bias by station (daily)")
    a1.tick_params(axis="x", rotation=90)
    a2.bar(stations, sd.r, color="tab:green")
    a2.set_ylabel("Pearson r"); a2.set_title("Correlation by station (daily)")
    a2.set_ylim(0, 1); a2.tick_params(axis="x", rotation=90)
    fig.tight_layout(); fig.savefig(PLOT_DIR / "bars_nmb_r_by_station.png", dpi=130)
    plt.close(fig)

    # 4. Diurnal cycle (mean obs vs model by hour)
    di = paired.groupby("hour").agg(obs=("obs", "mean"), model=("model", "mean"))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(di.index, di.obs, "-o", label="obs", color="black")
    ax.plot(di.index, di.model, "-o", label="model", color="tab:red")
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Mean PM2.5 (µg/m³)")
    ax.set_title("Mean diurnal cycle (all stations)"); ax.legend()
    fig.tight_layout(); fig.savefig(PLOT_DIR / "diurnal_cycle.png", dpi=130)
    plt.close(fig)

    # 5. Monthly mean cycle (obs vs model)
    mc = (paired.groupby("month").agg(obs=("obs", "mean"), model=("model", "mean")))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(mc.index, mc.obs, "-o", label="obs", color="black")
    ax.plot(mc.index, mc.model, "-o", label="model", color="tab:red")
    ax.set_xlabel("Month"); ax.set_ylabel("Mean PM2.5 (µg/m³)")
    ax.set_title("Mean monthly cycle (all stations)"); ax.legend()
    fig.tight_layout(); fig.savefig(PLOT_DIR / "monthly_cycle.png", dpi=130)
    plt.close(fig)

    # 6. Taylor diagram (daily, per station)
    taylor_diagram(daily, stations, PLOT_DIR / "taylor_diagram.png")

    # 7. Station bias map
    sd2 = by_station[by_station.resolution == "daily"].merge(coords, on="station")
    fig, ax = plt.subplots(figsize=(7, 8))
    vmax = np.nanmax(np.abs(sd2.MB))
    sc = ax.scatter(sd2.lon, sd2.lat, c=sd2.MB, s=160, cmap="RdBu_r",
                    vmin=-vmax, vmax=vmax, edgecolor="k", zorder=3)
    for _, r in sd2.iterrows():
        ax.annotate(r.station, (r.lon, r.lat), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title("Mean Bias (model − obs) by station, µg/m³ (daily)")
    fig.colorbar(sc, label="Mean Bias (µg/m³)")
    fig.tight_layout(); fig.savefig(PLOT_DIR / "bias_map.png", dpi=130)
    plt.close(fig)

    # 8. Q-Q plot (pooled distribution)
    q = np.linspace(1, 99, 99)
    oq, mq = np.percentile(paired.obs, q), np.percentile(paired.model, q)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(oq, mq, "-o", ms=3, color="tab:purple")
    hi = max(oq.max(), mq.max())
    ax.plot([0, hi], [0, hi], "r--", lw=1, label="1:1")
    ax.set_xlabel("Observed percentile PM2.5 (µg/m³)")
    ax.set_ylabel("Model percentile PM2.5 (µg/m³)")
    ax.set_title("Q–Q plot (1st–99th percentile)"); ax.legend()
    fig.tight_layout(); fig.savefig(PLOT_DIR / "qq_plot.png", dpi=130)
    plt.close(fig)


def taylor_diagram(daily, stations, outpath):
    """Simple Taylor diagram: normalized std vs correlation per station."""
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, polar=True)
    ax.set_thetamin(0); ax.set_thetamax(90)
    cmap = plt.cm.tab20(np.linspace(0, 1, len(stations)))
    for st, col in zip(stations, cmap):
        g = daily[daily.station == st]
        if g.obs.std() == 0 or len(g) < 3:
            continue
        r = np.corrcoef(g.obs, g.model)[0, 1]
        sd_ratio = g.model.std() / g.obs.std()
        ax.plot(np.arccos(np.clip(r, -1, 1)), sd_ratio, "o", color=col,
                label=st, ms=8)
    # reference point (obs)
    ax.plot(0, 1, "k*", ms=15, label="obs (ref)")
    ax.set_rmax(max(2.0, ax.get_rmax()))
    ax.set_title("Taylor diagram (daily, per station)\n"
                 "angle=correlation, radius=σ_model/σ_obs", fontsize=10)
    # correlation tick labels
    rticks = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99, 1.0]
    ax.set_xticks(np.arccos(rticks))
    ax.set_xticklabels([str(t) for t in rticks])
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=7)
    fig.tight_layout(); fig.savefig(outpath, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
