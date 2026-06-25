# Validation of Modeled PM2.5 against Bangladesh CAMS Monitors

**Period:** 1 October 2022 – 30 September 2023 (8,760 hourly steps)
**Model:** AELMO / WRF domain d02 fine-PM surface concentration, sampled at each
monitor's grid cell (`Brick_Kiln_Health_ERA5_GHRSST_d02_stdat_AELMO_Fine_rev.parquet`).
**Observations:** Bangladesh DoE Continuous Air Monitoring Stations (CAMS), 16
sites, hourly PM2.5 (consolidated from the 2012–2024 workbooks).
**Paired sample:** 108,006 station-hours after matching in space and time and
dropping hours with missing observations.

---

## 1. What was done

Model and observed PM2.5 were paired by station and timestamp, then evaluated
with the standard air-quality model-evaluation statistics recommended by
Emery et al. (2017) and Boylan & Russell (2006):

- **Bias / error (concentration units):** Mean Bias (MB), Mean Absolute Error
  (MAE), Root Mean Square Error (RMSE).
- **Normalized statistics (%):** Normalized Mean Bias (NMB), Normalized Mean
  Error (NME), Mean Fractional Bias (MFB), Mean Fractional Error (MFE).
- **Association:** Pearson correlation (r), coefficient of determination (R²),
  Willmott Index of Agreement (IOA), and the slope/intercept of the
  ordinary-least-squares fit `model = slope·obs + intercept`.

Statistics were computed (a) pooled across all stations, (b) per station,
(c) per calendar month and meteorological season, and (d) by hour of day, and
at three temporal resolutions: **hourly**, **daily-mean**, and **monthly-mean**.

Each grouping is flagged against the Boylan & Russell PM performance thresholds:

- **GOAL** (best achievable): |MFB| ≤ 30 % and MFE ≤ 50 %
- **CRITERIA** (acceptable): |MFB| ≤ 60 % and MFE ≤ 75 %
- **OUTSIDE**: neither met

---

## 2. Headline results

| Resolution | n | Obs mean | Model mean | MB | RMSE | NMB | NME | r | R² | IOA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hourly  | 108,006 | 89.5 | 47.1 | −42.4 | 83.7 | −47.4 % | 60.6 % | 0.56 | 0.32 | 0.67 |
| Daily   | 5,140 | 88.2 | 46.1 | −42.1 | 65.3 | −47.7 % | 53.9 % | 0.73 | 0.53 | 0.76 |
| Monthly | 189 | 86.5 | 46.2 | −40.3 | 51.3 | −46.6 % | 49.3 % | 0.84 | 0.71 | 0.80 |

*(Concentrations and errors in µg/m³.)*

**Two clear findings:**

1. **The model reproduces the timing and relative variability of pollution
   well, and better as you average over time.** Correlation rises from
   r = 0.56 (hourly) to 0.73 (daily) to 0.84 (monthly); R² reaches 0.71 at the
   monthly scale. The model gets *when* PM2.5 is high or low right.

2. **The model systematically under-predicts the magnitude by roughly a factor
   of two.** Mean modeled PM2.5 (~47 µg/m³) is about half the observed
   (~89 µg/m³); NMB ≈ −47 % at every resolution and the regression slope is
   ~0.5–0.7. This low bias is the dominant error and is why the overall
   fractional-bias statistics fall **outside** the Boylan–Russell criteria
   despite the good correlation.

---

## 3. By season

| Season | Obs mean | Model mean | NMB | NME | MFB | MFE | r | Benchmark |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| DJF (winter)      | 166.5 | 124.6 | −25.2 % | 49.9 % | −21.7 % | 56.4 % | 0.28 | **CRITERIA** |
| MAM (pre-monsoon) | 89.2 | 30.0 | −66.3 % | 69.3 % | −83.0 % | 91.7 % | 0.29 | OUTSIDE |
| JJA (monsoon)     | 37.8 | 10.1 | −73.3 % | 75.3 % | −112.2 % | 116.7 % | 0.37 | OUTSIDE |
| SON (post-monsoon)| 67.2 | 27.2 | −59.6 % | 65.7 % | −92.4 % | 100.6 % | 0.47 | OUTSIDE |

Performance is **best in winter (DJF)** — the high-pollution brick-firing season
— when the model meets the acceptance criteria and the absolute bias is
smallest in relative terms. The under-prediction worsens sharply in the
**pre-monsoon and monsoon** months, when the model collapses to near-zero
(monsoon model mean ~10 vs observed ~38 µg/m³). This is the classic signature of
**over-aggressive wet scavenging / boundary-layer dilution** or missing
non-kiln sources during the warm season.

---

## 4. By station (daily resolution)

Ranked by absolute bias. Only **Barishal** meets the acceptance criteria; the
remainder are dominated by the low bias.

| Station | Obs mean | Model mean | MB | NMB | r | IOA | Benchmark |
|---|---:|---:|---:|---:|---:|---:|---|
| Barishal    | 59.4 | 49.1 | −10.3 | −17.4 % | 0.85 | 0.91 | **CRITERIA** |
| Narsingdi   | 64.4 | 48.0 | −16.4 | −25.4 % | 0.64 | 0.79 | OUTSIDE |
| Cumilla     | 60.4 | 35.0 | −25.4 | −42.1 % | 0.62 | 0.72 | OUTSIDE |
| DoE         | 78.0 | 50.8 | −27.2 | −34.9 % | 0.86 | 0.89 | OUTSIDE |
| TV Sation   | 53.6 | 25.6 | −28.0 | −52.2 % | 0.34 | 0.47 | OUTSIDE |
| CDA         | 63.7 | 34.0 | −29.6 | −46.6 % | 0.81 | 0.79 | OUTSIDE |
| Khulna      | 76.4 | 45.9 | −30.4 | −39.8 % | 0.68 | 0.76 | OUTSIDE |
| Savar       | 84.1 | 48.5 | −35.6 | −42.3 % | 0.51 | 0.66 | OUTSIDE |
| BARC        | 103.0 | 59.8 | −43.3 | −42.0 % | 0.81 | 0.83 | OUTSIDE |
| Sylhet      | 72.8 | 25.7 | −47.1 | −64.7 % | 0.66 | 0.57 | OUTSIDE |
| Darussalam  | 112.3 | 58.3 | −54.0 | −48.1 % | 0.85 | 0.82 | OUTSIDE |
| Gazipur     | 105.7 | 52.6 | −53.1 | −50.3 % | 0.86 | 0.78 | OUTSIDE |
| Narayanganj | 122.8 | 62.9 | −60.0 | −48.8 % | 0.87 | 0.82 | OUTSIDE |
| Mymensing   | 103.6 | 40.9 | −62.6 | −60.5 % | 0.68 | 0.64 | OUTSIDE |
| Rajshahi    | 115.3 | 51.4 | −63.9 | −55.4 % | 0.77 | 0.68 | OUTSIDE |
| Rangpur     | 114.0 | 42.4 | −71.7 | −62.8 % | 0.83 | 0.66 | OUTSIDE |

Every station is biased low. The strongest under-prediction is at the northern
sites (Rangpur, Rajshahi, Mymensing) and the cleaner Sylhet site; the smallest
bias is at Barishal and Narsingdi. Correlation is strong (r ≥ 0.8) at the Dhaka
cluster (Darussalam, Gazipur, Narayanganj, BARC, DoE) — the model tracks Dhaka's
day-to-day variability very well even though it underestimates the level.

---

## 5. Diurnal behavior

Averaged over all stations and days, observed PM2.5 shows the expected
double-peaked urban cycle (morning and evening rush + nocturnal boundary-layer
collapse). The model reproduces the *shape* of the diurnal cycle but sits below
the observations at every hour, consistent with the overall low bias rather than
a timing error. (See `plots/diurnal_cycle.png`.)

---

## 6. Interpretation and suggested next steps

The validation supports a nuanced conclusion: **the model has skill at
reproducing the temporal structure of PM2.5 (especially aggregated to daily and
monthly scales and in the Dhaka region), but it underestimates absolute
concentrations by about a factor of two, with the deficit concentrated outside
the winter season.**

Plausible causes worth investigating with your advisor:

- **Emissions magnitude / coverage** — a uniform ~2× low bias often points to
  underestimated or missing emissions (e.g. sources beyond brick kilns:
  transport, biomass burning, secondary aerosol, transboundary transport).
- **Warm-season removal** — the collapse to near-zero in monsoon/pre-monsoon
  suggests wet deposition or vertical mixing may be too strong.
- **Representativeness mismatch** — a grid cell average is compared against a
  point monitor; several Dhaka stations share one grid cell (BARC, DoE,
  Darussalam), so very local hotspots cannot be resolved.
- **Boundary conditions / missing secondary PM** chemistry.

Recommended follow-ups:
1. Repeat the evaluation on **daily means** as the primary metric (less noisy,
   r = 0.73) and report monthly for the seasonal story.
2. Consider a **bias-correction / scaling factor** (slope ≈ 0.5–0.7) if the
   model is to be used for absolute exposure estimates.
3. Examine the **monsoon under-prediction** separately — it may warrant a
   wet-scavenging sensitivity test.
4. If a publication figure is needed, the per-station Taylor diagram and the
   daily scatter with the 1:1 line are the most informative.

---

## 7. Files

| File | Contents |
|---|---|
| `validate_model_vs_monitors.py` | Full reproducible analysis script |
| `metrics_overall.csv` | Pooled metrics at hourly / daily / monthly |
| `metrics_by_station.csv` | Per-station metrics (hourly + daily) |
| `metrics_by_month.csv` | Per calendar month |
| `metrics_by_season.csv` | Per meteorological season |
| `metrics_diurnal.csv` | Per hour of day |
| `paired_hourly.csv` | Tidy paired data (station, datetime, obs, model) |
| `plots/scatter_hourly_overall.png` | Hourly model-vs-obs density scatter, 1:1 |
| `plots/timeseries_daily_by_station.png` | Daily obs vs model, all 16 stations |
| `plots/bars_nmb_r_by_station.png` | NMB and correlation by station |
| `plots/diurnal_cycle.png` | Mean diurnal cycle, obs vs model |
| `plots/monthly_cycle.png` | Mean monthly cycle, obs vs model |
| `plots/taylor_diagram.png` | Taylor diagram (daily, per station) |
| `plots/bias_map.png` | Mean bias by station location |
| `plots/qq_plot.png` | Quantile–quantile, pooled distribution |

### Metric definitions
With model `m`, observation `o`, mean `̄x`, N pairs:
MB = mean(m−o); MAE = mean|m−o|; RMSE = √mean((m−o)²);
NMB = Σ(m−o)/Σo; NME = Σ|m−o|/Σo;
MFB = mean(2(m−o)/(m+o)); MFE = mean(2|m−o|/(m+o));
IOA = 1 − Σ(m−o)² / Σ(|m−ō| + |o−ō|)².

*References: Emery, C. et al. (2017), J. Air Waste Manage. Assoc. 67(5);
Boylan, J.W. & Russell, A.G. (2006), Atmos. Environ. 40.*
