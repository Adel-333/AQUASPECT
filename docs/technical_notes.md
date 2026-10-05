# AQUASPECT - Technical Notes

## 1. AOI Selection Rationale

**Selected Dual-AOI Strategy:**
1. **Lake Manzala, Northeast Nile Delta, Egypt** (Sentinel-2 12-month temporal baseline & anomaly analysis)
   - Bounding box (EPSG:4326): `[31.00°E, 30.90°N, 32.22°E, 31.35°N]`
2. **El Gouna Coast, Red Sea, Egypt** (Planet Tanager-1 426-band hyperspectral characterization)
   - Bounding box (EPSG:4326): `[33.511°E, 27.334°N, 33.758°E, 27.565°N]`

**Why Lake Manzala:**

| Criterion | Assessment |
|---|---|
| Water quality problem | Hypereutrophic; documented HABs (*Microcystis aeruginosa*); high turbidity |
| Optical signal strength | Strong - high chlorophyll and suspended sediment contrast across the lake |
| Sentinel-2 coverage | Full; ~5-day revisit; studied in peer-reviewed literature with S2 |
| Reference/validation data | CGLS LWQ 100m product (external benchmark); NIOF in-situ WQI data (published) |
| Spatial extent | ~572 km² - large enough for spatial statistics, manageable processing |
| Scientific defensibility | Most-published Egyptian water body in remote sensing literature |
| Change detection potential | Active restoration activities -> documented temporal signal |

---

## 2. Coordinate Reference System

**Target CRS for all spatial analysis:** EPSG:32636 (UTM Zone 36N)

**Why UTM 36N:**
- Covers the Nile Delta / Mediterranean coast / Sinai region
- Metric CRS -> correct area/distance calculations
- Avoids degree-based area approximations (which introduce ~40% error at 31°N)

---

## 3. Sentinel-2 Band Mapping

| S2 Band | Central λ (nm) | Resolution | Use in AQUASPECT |
|---|---|---|---|
| B03 | 560 | 10 m | Green - NDWI numerator; turbidity proxy denominator |
| B04 | 665 | 10 m | Red - NDWI/NDCI denominator; turbidity proxy numerator |
| B8A | 865 | 20 m | NIR - NDWI denominator; resampled to 10 m for alignment |
| SCL | - | 20 m | Scene Classification Layer - cloud/shadow/water masking |

**SCL cloud classes excluded:** 3 (cloud shadow), 8 (medium cloud), 9 (high cloud), 10 (thin cirrus)

---

## 4. Tanager Band Selection

Nearest-band lookup is performed at runtime using `preprocessing.nearest_band_index()` against the 426-band wavelength attribute stored in the HDF5 cube.

Reference wavelength targets:

| Target (nm) | Actual Tanager Band (nm) | Diagnostic use |
|---|---|---|
| 443 | 441.1 | Blue / coastal aerosol |
| 560 | 560.8 | Green / NDWI numerator |
| 665 | 665.9 | Red / chlorophyll absorption / NDCI denominator |
| 708 | 705.9 | Red-edge / NDCI numerator |
| 800 | 801.1 | NIR plateau |
| 860 | 861.3 | NIR2 / NDWI denominator |

Water-vapor absorption windows excluded from spectral plots:
- 1350-1450 nm
- 1800-1950 nm
- Far-SWIR tail excluded above 2450 nm.

---

## 5. Water Detection

**Method:** NDWI thresholding + connected-component filtering

**Formula:**
```
NDWI = (Green - NIR) / (Green + NIR)
```

**Threshold:** 0.0 (McFeeters default)
- Filter: Connected components with fewer than 100 pixels removed to eliminate isolated noise.
- Area calculation: Uses UTM pixel area (30 m x 30 m = 900 m² for Tanager; 10 m x 10 m = 100 m² for S2).

---

## 6. Chlorophyll / Algal-Bloom Screening

**Method:** NDCI (Normalised Difference Chlorophyll Index)

**Formula:**
```
NDCI = (R_708 - R_665) / (R_708 + R_665)
```

*Source: Mishra & Mishra (2012), Remote Sensing of Environment*

**Screening classes:**

| Class | Threshold | Label |
|---|---|---|
| 0 | NDCI <= 0.05 | Low chlorophyll indicator |
| 1 | 0.05 < NDCI <= 0.20 | Elevated chlorophyll indicator |
| 2 | NDCI > 0.20 | High chlorophyll indicator (potential bloom screening) |

*Note: These are screening thresholds only. Class 2 does NOT prove a toxic bloom without in-situ validation.*

---

## 7. Turbidity Proxy

**Method:** Red/Green normalised ratio

**Formula:**
```
Turbidity proxy = (R_665 - R_560) / (R_665 + R_560)
```

**Interpretation:** Higher values -> elevated red reflectance relative to green -> higher apparent suspended particulate matter.

*Dimensionless proxy: Calibration to physical turbidity units (NTU) requires concurrent in-situ calibration.*

---

## 8. Temporal Analysis / Anomaly Detection

**Baseline construction:**
- 8 distinct seasonal observations across 12 months (June 2024 - April 2025).
- Compute pixel-wise median and Median Absolute Deviation (MAD).

**Standardized Anomaly Metric:**
```
z = (observation - baseline_median) / max(baseline_MAD, 1e-4)
```

**Anomaly classification:**

| Z score | Class | Description |
|---|---|---|
| z < 1.0 | Normal | Baseline variability |
| 1.0 <= z < 2.0 | Elevated | Noticeable increase above annual median |
| 2.0 <= z < 3.0 | High | Significant positive deviation |
| z >= 3.0 | Extreme | Statistically extreme event (screening priority) |

---

## 9. Validation & Scientific Limitations

1. **Dual-AOI Strategy**:
   The open Tanager archive contains one confirmed Egyptian scene (El Gouna, Red Sea). The long-term temporal baseline was executed over Lake Manzala using Sentinel-2 L2A.

2. **Dimensionless Optical Proxies**:
   Indices are dimensionless optical proxies. Conversion to physical concentrations (µg/L Chl-a or NTU) requires concurrent local in-situ sampling.

3. **In-situ Availability**:
   Concurrent open in-situ data from Egyptian authorities (EEAA/NIOF) were not publicly accessible for the exact satellite acquisition dates.

4. **Atmospheric Correction**:
   Standard surface reflectance products (Tanager Ortho SR and Sentinel-2 Sen2Cor L2A) were utilized directly.
