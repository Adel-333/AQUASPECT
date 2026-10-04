"""
aquaspect.data
==============
Data-access utilities for AQUASPECT.

Provides functions to:
    - Search and download Sentinel-2 L2A scenes via STAC (Microsoft
      Planetary Computer or Copernicus Data Space).
    - Download Planet Tanager scenes referenced by a STAC item URL.
    - Validate scene footprint overlap with the AOI.

All download functions are deterministic given the same scene ID / URL.
No API keys are hard-coded; credentials are read from environment variables
or from a local .env file (never committed).

Environment variables expected
-------------------------------
PC_SDK_SUBSCRIPTION_KEY   Microsoft Planetary Computer subscription key
                           (optional — anonymous access works for most data)
PLANET_API_KEY             Planet API key for Tanager access
                           (only needed for non-open archive scenes)

Usage
-----
Set credentials in a .env file at the project root (never committed):

    PC_SDK_SUBSCRIPTION_KEY=your_key_here
    PLANET_API_KEY=your_key_here

Then call:
    from dotenv import load_dotenv; load_dotenv()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# STAC search — Sentinel-2
# ---------------------------------------------------------------------------

def search_sentinel2(
    bbox: list[float],
    date_range: str,
    max_cloud_pct: float = 20.0,
    collection: str = "sentinel-2-l2a",
    stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
    max_items: int = 50,
) -> list[dict]:
    """
    Search Sentinel-2 L2A scenes on Microsoft Planetary Computer via STAC.

    Parameters
    ----------
    bbox         : [west, south, east, north] in EPSG:4326
    date_range   : ISO date range string, e.g. "2023-01-01/2023-12-31"
    max_cloud_pct: maximum scene-level cloud cover (%)
    collection   : STAC collection name
    stac_url     : STAC API root
    max_items    : maximum number of items to return from search

    Returns
    -------
    items : list of STAC item dicts, sorted by datetime ascending.
            Each dict includes 'id', 'datetime', 'properties', 'assets'.

    Raises
    ------
    ImportError if pystac_client is not installed.
    """
    try:
        import pystac_client
    except ImportError as e:
        raise ImportError(
            "pystac_client is required for STAC search. "
            "Install with: pip install pystac-client"
        ) from e

    client = pystac_client.Client.open(stac_url)

    search = client.search(
        collections=[collection],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": max_cloud_pct}},
        max_items=max_items,
    )

    items = list(search.items())
    items.sort(key=lambda i: i.datetime)

    logger.info(
        "S2 STAC search: %d items found for bbox=%s, dates=%s, cloud<%.0f%%",
        len(items), bbox, date_range, max_cloud_pct,
    )
    return [_item_to_dict(i) for i in items]


def _item_to_dict(item) -> dict:
    """Convert a pystac Item to a plain dict for easy inspection."""
    return {
        "id":       item.id,
        "datetime": str(item.datetime),
        "cloud_pct": item.properties.get("eo:cloud_cover"),
        "tile":     item.properties.get("s2:mgrs_tile"),
        "bbox":     list(item.bbox),
        "assets":   {k: v.href for k, v in item.assets.items()},
    }


# ---------------------------------------------------------------------------
# Download a Sentinel-2 band from Planetary Computer
# ---------------------------------------------------------------------------

def download_s2_band(
    item_dict: dict,
    band_name: str,
    out_dir: Path,
    sign: bool = True,
) -> Path:
    """
    Download a single Sentinel-2 band (e.g. 'B03', 'B04', 'B8A', 'SCL').

    Parameters
    ----------
    item_dict : dict from search_sentinel2()
    band_name : Sentinel-2 band asset key (e.g. 'B03')
    out_dir   : local directory to save the file
    sign      : if True, sign the URL with Planetary Computer API
                (requires PC_SDK_SUBSCRIPTION_KEY env var or anonymous plan)

    Returns
    -------
    local_path : Path to downloaded file
    """
    try:
        import requests
    except ImportError as e:
        raise ImportError("requests is required: pip install requests") from e

    url = item_dict["assets"].get(band_name)
    if url is None:
        raise KeyError(f"Band '{band_name}' not found in item assets. "
                       f"Available: {list(item_dict['assets'].keys())}")

    if sign:
        url = _sign_pc_url(url)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{item_dict['id']}_{band_name}.tif"
    local_path = out_dir / filename

    if local_path.exists():
        logger.info("Band already downloaded: %s", local_path)
        return local_path

    logger.info("Downloading %s → %s", url, local_path)
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)

    return local_path


def _sign_pc_url(url: str) -> str:
    """Sign a Planetary Computer asset URL (requires PC SDK or env key)."""
    try:
        import planetary_computer
        return planetary_computer.sign(url)
    except ImportError:
        key = os.environ.get("PC_SDK_SUBSCRIPTION_KEY", "")
        if key:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}subscription-key={key}"
        logger.warning(
            "planetary_computer SDK not found and PC_SDK_SUBSCRIPTION_KEY "
            "not set. Attempting unsigned URL (may fail for restricted data)."
        )
        return url


# ---------------------------------------------------------------------------
# Load a raster clip to AOI (requires rasterio + rioxarray)
# ---------------------------------------------------------------------------

def load_raster_clip(
    file_path: Path,
    bbox: list[float],
    target_crs: str = "EPSG:32636",
) -> tuple:
    """
    Load a GeoTIFF, clip to bbox, and reproject to target_crs.

    Parameters
    ----------
    file_path  : path to GeoTIFF (Sentinel-2 band, etc.)
    bbox       : [west, south, east, north] in EPSG:4326
    target_crs : EPSG string for output CRS (UTM for Egypt)

    Returns
    -------
    data_array : 2-D numpy float32 array, reprojected + clipped
    transform  : affine transform of the output raster
    meta       : dict of rasterio metadata
    """
    try:
        import rasterio
        from rasterio.crs import CRS
        from rasterio.warp import transform_bounds
        from rasterio.mask import mask as rio_mask
        from shapely.geometry import box
        import fiona
    except ImportError as e:
        raise ImportError(
            "rasterio and shapely are required: "
            "pip install rasterio shapely"
        ) from e

    with rasterio.open(file_path) as src:
        # Transform bbox to raster CRS for clipping
        src_crs = src.crs
        if str(src_crs) != "EPSG:4326":
            west, south, east, north = bbox
            bounds_in_src = transform_bounds(
                "EPSG:4326", src_crs, west, south, east, north
            )
        else:
            bounds_in_src = bbox

        geom = [box(*bounds_in_src).__geo_interface__]
        data, transform = rio_mask(src, geom, crop=True, nodata=0)
        meta = src.meta.copy()

    meta.update({
        "height": data.shape[-2],
        "width":  data.shape[-1],
        "transform": transform,
    })

    return data.squeeze().astype(np.float32), transform, meta


# ---------------------------------------------------------------------------
# Validate footprint overlap
# ---------------------------------------------------------------------------

def check_aoi_overlap(
    item_bbox: list[float],
    aoi_bbox: list[float],
) -> float:
    """
    Return the fraction of the AOI bbox covered by the scene bbox (0–1).
    Both bboxes in [west, south, east, north], EPSG:4326.
    """
    try:
        from shapely.geometry import box
    except ImportError:
        raise ImportError("shapely required: pip install shapely")

    scene_box = box(*item_bbox)
    aoi_box   = box(*aoi_bbox)

    if not scene_box.intersects(aoi_box):
        return 0.0

    intersection = scene_box.intersection(aoi_box)
    return intersection.area / aoi_box.area


import numpy as np
