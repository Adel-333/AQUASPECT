"""
aquaspect.config
================
Central configuration for the AQUASPECT pipeline.

All AOI geometry, date ranges, file paths, thresholds and
spectral-band definitions live here so that every module
imports from a single source of truth.

Status: DRAFT — AOI, dates and scene ID will be filled in
after Phase 2 data-discovery is complete.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Repository root (resolves correctly when src/ is on PYTHONPATH)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR        = REPO_ROOT / "data"
SAMPLE_INPUT    = DATA_DIR / "sample_input"
RESULTS_DIR     = REPO_ROOT / "results"
FIGURES_DIR     = RESULTS_DIR / "figures"
MAPS_DIR        = RESULTS_DIR / "maps"
TABLES_DIR      = RESULTS_DIR / "tables"

# ---------------------------------------------------------------------------
# AOI — to be confirmed after data discovery
# ---------------------------------------------------------------------------
# Coordinates: [west, south, east, north]  (EPSG:4326, decimal degrees)
# PLACEHOLDER — replace with confirmed scene footprint
AOI_BBOX_WGS84 = None   # e.g. [31.0, 30.5, 32.5, 31.5]
AOI_NAME       = "TBD"  # e.g. "Lake Manzala"

# ---------------------------------------------------------------------------
# Target CRS for all spatial analysis
# ---------------------------------------------------------------------------
# Use a UTM zone appropriate for Egypt.
# Zone 36N (EPSG:32636) covers the Nile Delta / Sinai / Mediterranean coast.
# Zone 37N (EPSG:32637) covers eastern Egypt.
# Confirm the zone after AOI is fixed.
TARGET_CRS = "EPSG:32636"  # UTM Zone 36N — provisional

# ---------------------------------------------------------------------------
# Scene identifiers — to be filled after discovery
# ---------------------------------------------------------------------------
TANAGER_SCENE_ID  = None   # Planet Tanager scene ID (string)
TANAGER_ITEM_URL  = None   # STAC item URL for download
TANAGER_DATE      = None   # ISO 8601 acquisition date, e.g. "2024-06-15"

SENTINEL2_SCENES  = []     # list of Sentinel-2 item IDs for temporal stack

# ---------------------------------------------------------------------------
# Tanager spectral-band definitions
# (wavelengths in nm; indices derived after nearest-band lookup)
# Source: Planet Tanager product documentation / hackathon reference material
# ---------------------------------------------------------------------------
TANAGER_BAND_WAVELENGTHS = {
    # Key diagnostic wavelengths used in water-quality indicators
    "blue":     443,   # coastal aerosol / deep water
    "green":    560,   # peak water reflectance / NDWI
    "red":      665,   # chlorophyll absorption trough
    "red_edge": 708,   # chlorophyll fluorescence shoulder
    "nir":      800,   # NIR plateau
    "nir2":     860,   # second NIR / NDWI denominator
}

# Water-vapour absorption windows to exclude from spectral analysis
WATER_VAPOUR_WINDOWS_NM = [
    (1350, 1450),
    (1800, 1950),
]
FAR_SWIR_CUTOFF_NM = 2450  # exclude tail above this

# ---------------------------------------------------------------------------
# Quality-mask field names (Tanager HDF5)
# ---------------------------------------------------------------------------
TANAGER_QA = {
    "reflectance_path": "HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance",
    "nodata_mask":      "nodata_pixels",
    "cloud_mask":       "beta_cloud_mask",
    "cirrus_mask":      "beta_cirrus_mask",
}

# ---------------------------------------------------------------------------
# Water-detection thresholds
# ---------------------------------------------------------------------------
# NDWI threshold — empirical, validated against reference water mask.
# Literature common starting point: 0.0 (McFeeters 1996).
# This value MUST be documented and validated for the chosen scene.
NDWI_WATER_THRESHOLD = 0.0   # PROVISIONAL — validate before finalising

# ---------------------------------------------------------------------------
# Chlorophyll / algal-bloom screening
# ---------------------------------------------------------------------------
# NDCI screening threshold.
# Reference: Mishra & Mishra (2012) suggest NDCI > 0 broadly indicates
# elevated chlorophyll; >0.2 is sometimes used as a HIGH indicator.
# This is a SCREENING threshold, not a calibrated bloom detector.
NDCI_SCREEN_HIGH  = 0.2    # candidate high-chlorophyll screen
NDCI_SCREEN_ELEV  = 0.05   # candidate elevated-chlorophyll screen

# ---------------------------------------------------------------------------
# Spatial-statistics parameters
# ---------------------------------------------------------------------------
MIN_WATER_PIXELS = 100  # minimum connected-component size to keep

# ---------------------------------------------------------------------------
# Sentinel-2 configuration (for temporal comparison / validation)
# ---------------------------------------------------------------------------
S2_COLLECTION = "sentinel-2-l2a"
S2_CLOUD_MAX_PCT = 20   # maximum scene-level cloud cover to accept
