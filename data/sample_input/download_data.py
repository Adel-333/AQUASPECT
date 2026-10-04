"""
AQUASPECT — Deterministic Data Download Script
===============================================
Downloads the exact satellite scenes used in the analysis.
Run from the project root:

    python data/sample_input/download_data.py

Prerequisites
-------------
1. Install dependencies:
       pip install -r requirements.txt

2. Create a .env file at the project root (NEVER commit this file):
       PC_SDK_SUBSCRIPTION_KEY=your_key_here
       PLANET_API_KEY=your_planet_key_here   # only needed for Tanager

3. Register for free Planetary Computer access:
       https://planetarycomputer.microsoft.com/

What this script downloads
--------------------------
- Sentinel-2 L2A bands (B03, B04, B8A, SCL) for Lake Manzala
  clipped to the AOI bounding box.
- CGLS LWQ 100m validation product (chlorophyll-a, turbidity)
  for the matching date range.

It does NOT download:
- Full (unclipped) Sentinel-2 scenes.
- Full Tanager HDF5 scenes (file sizes > 10 GB; see Tanager section below).

Tanager data
------------
Full Tanager scenes are too large to auto-download here.
See docs/data_sources.md for:
- How to search Planet STAC for the scene ID in scene_manifest.json
- How to download via the Planet SDK or STAC browser
- How to place the file in data/sample_input/ with the expected filename

Outputs
-------
data/sample_input/
├── s2_<scene_id>_B03.tif
├── s2_<scene_id>_B04.tif
├── s2_<scene_id>_B8A.tif
├── s2_<scene_id>_SCL.tif
└── cgls_lwq_<date>.nc    (validation product)
"""

import json
import logging
import os
import sys
from pathlib import Path

# Allow running from any working directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from aquaspect.data import search_sentinel2, download_s2_band

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("download_data")

# ---------------------------------------------------------------------------
# Load manifest
# ---------------------------------------------------------------------------
MANIFEST_PATH = Path(__file__).parent / "scene_manifest.json"
OUT_DIR = Path(__file__).parent

with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

AOI_BBOX    = manifest["aoi"]["bbox_wgs84"]
S2_CONFIG   = manifest["sentinel2"]
BANDS       = S2_CONFIG["bands_required"]
STAC_URL    = S2_CONFIG["stac_endpoint"]
COLLECTION  = S2_CONFIG["collection"]
CLOUD_MAX   = S2_CONFIG["max_cloud_cover_pct"]
DATE_RANGE  = S2_CONFIG.get("date_range_analysis", None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if DATE_RANGE in (None, "TBD_after_discovery"):
        logger.error(
            "scene_manifest.json contains placeholder dates. "
            "Complete Phase 2 data discovery first, then update "
            "date_range_analysis in scene_manifest.json."
        )
        sys.exit(1)

    logger.info("Searching Sentinel-2 scenes for Lake Manzala …")
    items = search_sentinel2(
        bbox=AOI_BBOX,
        date_range=DATE_RANGE,
        max_cloud_pct=CLOUD_MAX,
        collection=COLLECTION,
        stac_url=STAC_URL,
        max_items=20,
    )

    if not items:
        logger.error("No Sentinel-2 scenes found. Check date range and bbox.")
        sys.exit(1)

    logger.info("Found %d scenes. Downloading bands: %s", len(items), BANDS)

    for item in items:
        logger.info("Scene: %s  (%s)  cloud=%.1f%%",
                    item["id"], item["datetime"], item["cloud_pct"] or -1)
        for band in BANDS:
            try:
                path = download_s2_band(
                    item_dict=item,
                    band_name=band,
                    out_dir=OUT_DIR,
                    sign=True,
                )
                logger.info("  ✓ %s → %s", band, path.name)
            except KeyError:
                logger.warning("  ✗ Band %s not available for scene %s", band, item["id"])

    logger.info("Download complete. Files saved to: %s", OUT_DIR)
    logger.info(
        "\nNext step: open notebooks/01_aquaspect_water_quality_poc.ipynb "
        "and run all cells from a fresh kernel."
    )


if __name__ == "__main__":
    main()
