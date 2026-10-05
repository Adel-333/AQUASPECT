# AQUASPECT - Data Sources

## Satellite Data

### 1. Sentinel-2 MSI Level-2A

| Property | Value |
|---|---|
| Provider | European Space Agency (ESA) / Copernicus Programme |
| Product | Sentinel-2 MSI L2A (atmospherically corrected surface reflectance) |
| Spatial resolution | 10 m (B03, B04), 20 m (B8A), 20 m (SCL) |
| Temporal resolution | ~5 days (two-satellite constellation) |
| Bands used | B03 (560 nm Green), B04 (665 nm Red), B8A (865 nm NIR), SCL (Scene Classification) |
| Access | Microsoft Planetary Computer STAC API |
| STAC endpoint | `https://planetarycomputer.microsoft.com/api/stac/v1` |
| Collection | `sentinel-2-l2a` |
| Licence | Copernicus Sentinel Data Terms and Conditions (free reuse with attribution) |
| Licence URL | https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice |

**Scenes used in 12-Month Baseline & Anomaly Analysis:**

| Date | Tile / Granule ID | Cloud % | Water Pixels | Role |
|---|---|---|---|---|
| 2024-06-06 | T36RUV | 0.00% | 41,889 | 12-Month Baseline Stack |
| 2024-07-21 | T36RTV | 0.00% | 19,329 | 12-Month Baseline Stack |
| 2024-08-20 | T36RTV | 0.00% | 20,143 | 12-Month Baseline Stack |
| 2024-09-27 | T36RUV | 0.00% | 28,252 | 12-Month Baseline Stack |
| 2024-10-04 | T36RVV | 5.94% | 410,013 | 12-Month Baseline Stack |
| 2024-12-28 | T36RVV (20241228T093822) | 0.05% | 466,347 | 12-Month Baseline Stack |
| 2025-01-30 | T36RUV (20250130T124050) | 0.03% | 48,003 | 12-Month Baseline Stack |
| 2025-04-27 | T36RTV | 3.97% | 41,281 | Analysis Target (Anomaly Screening) |

---

### 2. Planet Tanager-1 Hyperspectral

| Property | Value |
|---|---|
| Provider | Planet Labs PBC |
| Satellite | Tanager-1 |
| Product | Surface Reflectance (ortho_sr_hdf5) |
| Spectral bands | 426 bands, ~376-2499 nm |
| Spatial resolution | ~33 m GSD |
| HDF5 dataset path | `HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance` |
| Access | Planet Open Archive / STAC API |
| STAC endpoint | `https://www.planet.com/data/stac/` |
| Licence | Open Archive (CC-BY-4.0) |
| Licence URL | https://www.planet.com/markets/education-and-research/ |

**Key wavelengths selected:**

| Purpose | Target (nm) | Nearest Tanager band (nm) |
|---|---|---|
| Blue / coastal aerosol | 443 | 441.1 |
| Green / NDWI numerator | 560 | 560.8 |
| Red / chlorophyll abs. | 665 | 665.9 |
| Red-edge / NDCI numerator | 708 | 705.9 |
| NIR plateau | 800 | 801.1 |
| NIR2 / NDWI denominator | 860 | 861.3 |

**Tanager scene used:**

| Scene ID | Acquisition Date | Cloud % | AOI & Bounding Box | Role |
|---|---|---|---|---|
| `20250926_092059_95_4001` | 2025-09-26T09:20:59Z | 0.00% | El Gouna, Red Sea `[33.511°E, 27.334°N, 33.758°E, 27.565°N]` | Hyperspectral 426-band extraction & screening |

---

## Validation Data

### 3. CGLS Lake Water Quality 100m V2.0

| Property | Value |
|---|---|
| Provider | Copernicus Global Land Service (CGLS) |
| Product | Lake Water Quality 100m (LWQ100) V2.0 |
| Parameters | Chlorophyll-a (µg/L), Turbidity/TSM (FNU), Trophic State Index, Cyanobacteria risk |
| Temporal resolution | 10-day composites |
| Spatial resolution | 100 m |
| Coverage | Global lakes > 50 ha; Lake Manzala confirmed |
| Period | 2019-present |
| Access | https://land.copernicus.eu/ |
| Licence | Copernicus Land Monitoring Service data policy (free reuse with attribution) |

### 4. JRC Global Surface Water (GSW)

| Property | Value |
|---|---|
| Provider | European Commission Joint Research Centre |
| Product | JRC Global Surface Water Explorer |
| Parameters | Water occurrence, seasonality, extent (Landsat-based 1984-present) |
| Spatial resolution | 30 m |
| Licence | CC BY 4.0 |
| Access | https://global-surface-water.appspot.com/ |

### 5. Published In-situ Measurements - Lake Manzala

Studies to be used as reference (full citations in technical notes):

- NIOF (National Institute of Oceanography and Fisheries, Egypt) - multi-station WQI sampling 2021-2023
- Published Trophic State Index (TSI) and Water Quality Index (WQI) values for Lake Manzala
  from NIH/PubMed-indexed papers and Egyptian Journal of Aquatic Research
- Phytoplankton distribution studies with concurrent physicochemical measurements

> **Note:** In-situ data is extracted from peer-reviewed publications, not from a direct
> government API. Exact station coordinates and measurement dates are recorded in the
> notebook validation section.

---

## Attribution Statement

When publishing or presenting results, include:

```
Sentinel-2 imagery: ESA/Copernicus, accessed via Microsoft Planetary Computer.
Tanager hyperspectral imagery: Planet Labs PBC.
CGLS LWQ validation product: Copernicus Global Land Service.
JRC GSW water extent: European Commission JRC.
In-situ reference data: [specific paper citations - see technical_notes.md].
```
