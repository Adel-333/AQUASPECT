# AQUASPECT — Data Sources

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

**Scenes used (to be completed after discovery):**

| Scene ID | Acquisition Date | Cloud % | Role |
|---|---|---|---|
| TBD | TBD | TBD | Baseline |
| TBD | TBD | TBD | Analysis |

---

### 2. Planet Tanager-1 Hyperspectral

| Property | Value |
|---|---|
| Provider | Planet Labs PBC |
| Satellite | Tanager-1 |
| Product | Surface Reflectance |
| Spectral bands | 426 bands, ~376–2499 nm |
| Spatial resolution | ~30 m |
| HDF5 dataset path | `HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance` |
| Access | Planet STAC API (Education & Research Programme) |
| STAC endpoint | `https://www.planet.com/data/stac/` |
| Licence | Planet Education & Research Programme terms |
| Licence URL | https://www.planet.com/markets/education-and-research/ |

**Key wavelengths selected:**

| Purpose | Target (nm) | Nearest Tanager band (nm) |
|---|---|---|
| Blue / coastal aerosol | 443 | ~441.1 |
| Green / NDWI numerator | 560 | ~560.8 |
| Red / chlorophyll abs. | 665 | ~665.9 |
| Red-edge / NDCI numerator | 708 | ~705.9 |
| NIR plateau | 800 | ~801.1 |
| NIR2 / NDWI denominator | 860 | ~861.3 |

**Tanager scene used (to be completed after discovery):**

| Scene ID | Acquisition Date | Cloud % | AOI overlap % |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

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
| Period | 2019–present |
| Access | https://land.copernicus.eu/ |
| Licence | Copernicus Land Monitoring Service data policy (free reuse with attribution) |

### 4. JRC Global Surface Water (GSW)

| Property | Value |
|---|---|
| Provider | European Commission Joint Research Centre |
| Product | JRC Global Surface Water Explorer |
| Parameters | Water occurrence, seasonality, extent (Landsat-based 1984–present) |
| Spatial resolution | 30 m |
| Licence | CC BY 4.0 |
| Access | https://global-surface-water.appspot.com/ |

### 5. Published In-situ Measurements — Lake Manzala

Studies to be used as reference (full citations in technical notes):

- NIOF (National Institute of Oceanography and Fisheries, Egypt) — multi-station WQI sampling 2021–2023
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
In-situ reference data: [specific paper citations — see technical_notes.md].
```
