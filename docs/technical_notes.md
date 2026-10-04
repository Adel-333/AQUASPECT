# AQUASPECT — Technical Notes

## 1. AOI Selection Rationale

**Selected AOI:** Lake Manzala, Northeast Nile Delta, Egypt

**Bounding box (EPSG:4326):** `[31.00, 30.90, 32.22, 31.35]`

**Why Lake Manzala:**

| Criterion | Assessment |
|---|---|
| Water quality problem | Hypereutrophic; documented HABs (*Microcystis aeruginosa*); high turbidity |
| Optical signal strength | Strong — high chlorophyll and suspended sediment contrast across the lake |
| Sentinel-2 coverage | Full; ~5-day revisit; studied in peer-reviewed literature with S2 |
| Reference/validation data | CGLS LWQ 100m product (external benchmark); NIOF in-situ WQI data (published) |
| Spatial extent | ~572 km² — large enough for spatial statistics, small enough for manageable download |
| Scientific defensibility | Most-published Egyptian water body in remote sensing literature |
| Change detection potential | Active restoration activities → documented temporal signal |

**Rejected candidates:**

- Lake Burullus — strong published matchup data (MDPI 2022) but less severe HAB signal than Manzala for hyperspectral demonstration
- Lake Qarun — inland/hypersaline, good for salinity/turbidity but less chlorophyll signal
- Lake Mariout — too small (~50 km²) for robust spatial statistics; weak published matchup data
- UAE starter AOI — explicitly excluded per project brief

---

## 2. Coordinate Reference System

**Target CRS for all spatial analysis:** EPSG:32636 (UTM Zone 36N)

**Why UTM 36N:**
- Covers the Nile Delta / Mediterranean coast / Sinai region
- Metric CRS → correct area/distance calculations
- Avoids degree-based area approximations (which introduce ~40% error at 31°N)

**All rasters are reprojected to EPSG:32636 before pixel-wise comparison.**

---

## 3. Sentinel-2 Band Mapping

| S2 Band | Central λ (nm) | Resolution | Use in AQUASPECT |
|---|---|---|---|
| B03 | 560 | 10 m | Green — NDWI numerator; turbidity proxy denominator |
| B04 | 665 | 10 m | Red — NDWI/NDCI denominator; turbidity proxy numerator |
| B8A | 865 | 20 m | NIR — NDWI denominator; resampled to 10 m for alignment |
| SCL | — | 20 m | Scene Classification Layer — cloud/shadow/water masking |

**SCL cloud classes excluded:** 3 (cloud shadow), 8 (medium cloud), 9 (high cloud), 10 (thin cirrus)

---

## 4. Tanager Band Selection

Nearest-band lookup is performed at runtime using `preprocessing.nearest_band_index()`.
The actual band index depends on the specific scene's wavelength array stored in the HDF5.

Reference wavelength targets (from hackathon documentation):

| Target (nm) | Expected actual (nm) | Diagnostic use |
|---|---|---|
| 443 | ~441.1 | Blue / coastal aerosol |
| 560 | ~560.8 | Green / NDWI |
| 665 | ~665.9 | Red / chlorophyll abs. / NDCI denominator |
| 708 | ~705.9 | Red-edge / NDCI numerator |
| 800 | ~801.1 | NIR plateau |
| 860 | ~861.3 | NIR2 / NDWI denominator |

Water-vapour absorption windows excluded from spectral plots:
- 1350–1450 nm
- 1800–1950 nm

Far-SWIR tail excluded above 2450 nm.

---

## 5. Water Detection

**Method:** NDWI thresholding + connected-component filtering

**Formula:**
```
NDWI = (Green − NIR) / (Green + NIR)
```

**Threshold:** 0.0 (McFeeters 1996 default)
- This is an **empirical starting value** validated against the JRC GSW
  water occurrence layer for the selected scene.
- If accuracy is insufficient, the threshold is adjusted and documented.

**Post-processing:** Connected components with fewer than 100 pixels removed
to eliminate isolated noise detections.

**Area calculation:** Uses UTM pixel area (30 m × 30 m = 900 m² for Tanager;
10 m × 10 m = 100 m² for S2 B03/B04). Not degree-based.

---

## 6. Chlorophyll / Algal-bloom Screening

**Method:** NDCI (Normalised Difference Chlorophyll Index)

**Formula:**
```
NDCI = (R_708 − R_665) / (R_708 + R_665)
```

**Source:** Mishra & Mishra (2012), Remote Sensing of Environment

**Screening classes:**

| Class | Threshold | Label |
|---|---|---|
| 0 | NDCI ≤ 0.05 | Low chlorophyll indicator |
| 1 | 0.05 < NDCI ≤ 0.20 | Elevated chlorophyll indicator |
| 2 | NDCI > 0.20 | High chlorophyll indicator (potential bloom screening) |

**IMPORTANT:** These are screening thresholds only. Class 2 does NOT prove
an algal bloom without independent validation. Outputs are labelled
"candidate high-chlorophyll pixels" in all maps and tables.

---

## 7. Turbidity Proxy

**Method:** Red/Green normalised ratio

**Formula:**
```
Turbidity proxy = (R_665 − R_560) / (R_665 + R_560)
```

**Interpretation:** Higher values → elevated red relative to green →
higher apparent suspended particulate load.

**NOT in NTU.** Calibration to physical turbidity units requires
concurrent in-situ measurements, which are noted as a limitation.

---

## 8. Temporal Analysis / Anomaly Detection

**Baseline construction:**
- Collect all valid Sentinel-2 observations within the baseline date range
- Apply identical preprocessing to each date
- Compute pixel-wise median and MAD (robust statistics chosen because the
  baseline sample is small: typically 5–15 dates)

**Anomaly metric:**
```
z = (observation − baseline_median) / max(baseline_MAD, 1e-4)
```

**Anomaly classes:**

| z score | Class |
|---|---|
| z ≤ 0 | Normal |
| 0 < z < 2 | Elevated |
| 2 ≤ z < 3 | High anomaly |
| z ≥ 3 | Extreme anomaly |

**Cloud contamination prevention:** Only pixels with valid SCL classification
(water class = 6) are included. Cloudy pixels set to NaN propagate correctly.

---

## 9. Validation Strategy

**Layer 1 — Water mask validation:**
- Reference: JRC GSW water occurrence layer (Landsat-based permanent water)
- Metrics: Precision, Recall, F1, IoU
- Limitation: JRC is long-term average, not date-specific

**Layer 2 — Chlorophyll screening benchmark:**
- Reference: CGLS LWQ 100m chlorophyll-a product (10-day composite)
- Comparison: Spatial agreement of elevated NDCI zones with CGLS high-Chl-a pixels
- Metric: Spearman correlation, spatial overlap

**Layer 3 — Published in-situ reference:**
- Reference: Published WQI / trophic state data from NIOF and peer-reviewed papers
- Comparison: Qualitative agreement of north/south pollution gradient
- Limitation: Station coordinates from published papers may not align perfectly
  with the analysis date

**When validation is not possible:**
`validation.validation_not_possible()` is called with an explicit reason
and saved to `results/tables/validation_summary.csv`.

---

## 10. Known Limitations

1. **Tanager coverage uncertainty** — Egyptian scene coverage is being verified;
   if no direct Manzala scene exists, the analysis will use the closest available
   scene and note this explicitly.

2. **Atmospheric correction** — Tanager surface reflectance product is used directly.
   S2 uses L2A (Sen2Cor corrected). No additional water-column correction (e.g.
   C2RCC, ACOLITE) is applied in the initial version — a noted limitation.

3. **No calibrated physical units** — NDCI and turbidity proxy are dimensionless
   screening indicators. Physical units (µg/L, NTU) require calibration not
   performed in this PoC.

4. **CGLS LWQ temporal mismatch** — 10-day composites may not exactly match
   the Tanager/S2 acquisition date.

5. **Small baseline sample** — Depending on cloud cover frequency over Manzala,
   the baseline may contain fewer than 10 valid S2 dates. MAD-based statistics
   are used to compensate, but uncertainty remains high.
