# AQUASPECT
## Egypt Water Quality & Inland/Coastal Water Intelligence

**A Proof of Concept for the Arab Youth Space Hackathon (813 Challenge) — Theme 6: Water Quality**

---

## 1. Business Use Case
AQUASPECT provides environmental monitoring teams, coastal management authorities, and water-resource managers with an early-warning intelligence system. It translates complex hyperspectral and multispectral satellite data into actionable screening maps for potential harmful algal blooms (HABs), suspended sediment plumes, and structural water-quality anomalies before they cause critical damage to fisheries, desalination intakes, or coastal ecosystems.

## 2. The Problem
Egypt's inland and coastal waters—including critical ecosystems like Lake Manzala and Red Sea coastal zones—face mounting pressure from agricultural drainage, industrial discharge, and urban wastewater. Current monitoring relies heavily on sparse, expensive, and time-consuming in-situ sampling. Decision-makers lack high-frequency, spatially continuous intelligence to identify emerging pollution hotspots or track the extent of eutrophication events across large water bodies.

## 3. Data Used
This project adopts a **Dual-AOI Strategy** to demonstrate both hyperspectral capabilities and robust temporal validation:

1. **Planet Tanager-1 Hyperspectral (El Gouna, Red Sea)**
   - Used to demonstrate hyperspectral capability (426 bands, ~376–2499 nm).
   - Acquired: 26 Sept 2025. This is the only confirmed open-archive Tanager scene over Egypt.
   - Provides deep spectral analysis of marine/coastal waters.

2. **Copernicus Sentinel-2 L2A (Lake Manzala, Nile Delta)**
   - Used for the temporal anomaly detection and cross-validation baseline.
   - Lake Manzala is Egypt's largest coastal lagoon and possesses the strongest published reference data (NIOF/NIH studies).

**Validation Data:** Copernicus Global Land Service (CGLS) Lake Water Quality 100m product and published in-situ Water Quality Index (WQI) measurements.

## 4. Technical Approach
AQUASPECT moves beyond simple static indices. The end-to-end pipeline includes:
1. **Deterministic Data Retrieval**: Programmatic STAC search and retrieval.
2. **Preprocessing & Quality Control**: Exclusion of water-vapor bands, SWIR-edge noise, and cloud/cirrus pixels using provided HDF5 QA masks.
3. **Water Detection**: NDWI-based water extraction with connected-component filtering to remove noise.
4. **Hyperspectral Screening**: Extraction of specific spectral features (e.g., NDCI for chlorophyll proxy, Red/Green for turbidity) using targeted wavelength lookups.
5. **Temporal Anomaly Detection (z-score)**: For multispectral data, computing pixel-wise median and Median Absolute Deviation (MAD) baselines to flag statistically significant deviations.
6. **Validation**: Honest comparison against independent external data (CGLS LWQ) and published ground-truth locations, outputting concrete metrics where available, and explicitly documenting limitations where not.

## 5. Installation
Requires Python 3.10+.

```bash
git clone <your-repository-url>
cd AQUASPECT
pip install -r requirements.txt
```

Set up credentials (never commit this file):
Create a `.env` file in the project root:
```env
PC_SDK_SUBSCRIPTION_KEY=your_planetary_computer_key
PLANET_API_KEY=your_planet_key
```

## 6. How to Run
1. **Download Data**: Fetch the required Sentinel-2 bands based on the exact STAC queries configured in the manifest:
   ```bash
   python src/aquaspect/data.py
   # Or run: python data/sample_input/download_data.py
   ```
2. **Execute Analysis**: Open the main Jupyter notebook and run all cells from a clean kernel:
   ```bash
   jupyter lab notebooks/01_aquaspect_water_quality_poc.ipynb
   ```

## 7. Example Input and Output
**Input**:
- Planet Tanager HDF5 Surface Reflectance cube
- Sentinel-2 L2A B03, B04, B8A, SCL GeoTIFFs

**Output** (saved in `results/maps/` and `results/figures/`):
- `water_mask.png`: Refined water extraction
- `chlorophyll_indicator.png`: Three-class screening map for potential HABs
- `turbidity_indicator.png`: Dimensionless suspended material proxy
- `anomaly_map.png`: Standardised z-score anomaly map
- `time_series.png`: Baseline vs. current observation temporal plot
- `validation_summary.csv`: Computed accuracy metrics

## 8. Results and Limitations
**Results**:
- Successfully separated water from land/vegetation using combined spectral indices.
- Generated chlorophyll and turbidity proxy maps highlighting known pollution gradients (e.g., Manzala south-to-north gradient).

**Limitations**:
- **Geographic Data Constraints**: Commercial Tanager data over Nile Delta lakes was not available in the open archive; we utilized the El Gouna Red Sea scene for the hyperspectral component.
- **Physical Calibration**: Output indices are unitless proxies for screening. Conversion to exact µg/L (chlorophyll) or NTU (turbidity) requires concurrent in-situ spectral calibration.
- **Atmospheric Correction**: Used standard surface reflectance products; specialized inland-water atmospheric correction (e.g., C2RCC) was out of scope for this initial PoC.

## 9. Team, Licence and Attribution
- **Team**: [Your Team Name / Members]
- **Licence**: MIT License (see `LICENSE` file for details).
- **Attribution**:
  - Planet Tanager data: CC-BY-4.0 © Planet Labs PBC
  - Sentinel-2 data: ESA / Copernicus Programme
  - See `docs/data_sources.md` for a complete list of citations and acknowledgements.
