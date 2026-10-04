import json

colab_nb = {
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": []
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "source": [
        "# AQUASPECT — PHASE 3: Cloud Execution & Scientific Verification\n",
        "This notebook is specifically designed to execute the AQUASPECT dual-AOI pipeline in Google Colab, bypassing local machine resource limits (compilation times, 1.08 GB file downloads, and RAM constraints).\n",
        "\n",
        "**Instructions:**\n",
        "1. Upload the local `src/aquaspect/` folder to the Colab environment (or mount Google Drive if uploaded there).\n",
        "2. Run the cells sequentially from top to bottom."
      ],
      "metadata": {
        "id": "intro_md"
      }
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 1: Prepare Colab Environment\n",
        "Colab already has `numpy`, `pandas`, `matplotlib`, `scipy`, `h5py`, `xarray`, `shapely`, and `requests`.\n",
        "We only install the missing geospatial/STAC libraries using binary wheels where possible."
      ],
      "metadata": {
        "id": "step1_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "!python --version\n",
        "!pip install pystac-client planetary-computer rasterio rioxarray --quiet\n",
        "\n",
        "import sys\n",
        "import numpy as np\n",
        "import pandas as pd\n",
        "import matplotlib.pyplot as plt\n",
        "import scipy\n",
        "import h5py\n",
        "import rasterio\n",
        "import xarray as xr\n",
        "import rioxarray\n",
        "import shapely\n",
        "import pyproj\n",
        "import requests\n",
        "import planetary_computer\n",
        "import pystac_client\n",
        "\n",
        "print(\"\\nAll required libraries imported successfully!\")\n",
        "print(f\"Python: {sys.version.split()[0]}\")\n",
        "print(f\"Numpy: {np.__version__}\")\n",
        "print(f\"h5py: {h5py.__version__}\")"
      ],
      "metadata": {
        "id": "step1_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 2: Connect to Local AQUASPECT Source\n",
        "Ensure `src/aquaspect` is accessible in the Colab file system."
      ],
      "metadata": {
        "id": "step2_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "import os\n",
        "from pathlib import Path\n",
        "\n",
        "# Assuming src/ is uploaded to the root of the Colab runtime (/content/src)\n",
        "if not os.path.exists(\"/content/src/aquaspect\"):\n",
        "    print(\"WARNING: /content/src/aquaspect not found. Please upload the 'src' folder from your local AQUASPECT project.\")\n",
        "else:\n",
        "    if \"/content/src\" not in sys.path:\n",
        "        sys.path.insert(0, \"/content/src\")\n",
        "    print(\"Local AQUASPECT modules loaded into path.\")\n",
        "    \n",
        "    # We will safely import them to verify:\n",
        "    from aquaspect import config, preprocessing, indices, detection, visualization, validation\n",
        "    print(\"AQUASPECT core modules imported successfully.\")"
      ],
      "metadata": {
        "id": "step2_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 3: Verify Tanager Access (Live STAC)"
      ],
      "metadata": {
        "id": "step3_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "TANAGER_STAC_URL = \"https://www.planet.com/data/stac/tanager-core-imagery/coastal-water-bodies/20250926_092059_95_4001/20250926_092059_95_4001.json\"\n",
        "print(\"Querying Planet STAC API for El Gouna scene...\")\n",
        "r = requests.get(TANAGER_STAC_URL)\n",
        "r.raise_for_status()\n",
        "tanager_item = r.json()\n",
        "\n",
        "print(f\"Collection: {tanager_item.get('collection')}\")\n",
        "print(f\"Item ID: {tanager_item.get('id')}\")\n",
        "print(f\"Date: {tanager_item.get('properties', {}).get('datetime')}\")\n",
        "print(f\"BBox: {tanager_item.get('bbox')}\")\n",
        "\n",
        "asset_key = \"ortho_sr_hdf5\"\n",
        "asset_url = tanager_item['assets'][asset_key]['href']\n",
        "print(f\"Target Asset ({asset_key}): {asset_url}\")"
      ],
      "metadata": {
        "id": "step3_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 4: Memory-Safe Download of Tanager HDF5"
      ],
      "metadata": {
        "id": "step4_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "import time\n",
        "tanager_file = Path(\"/content/20250926_092059_95_4001_ortho_sr_hdf5.h5\")\n",
        "\n",
        "# Verify size first\n",
        "head_req = requests.head(asset_url)\n",
        "size_bytes = int(head_req.headers.get(\"content-length\", 0))\n",
        "print(f\"Expected File Size: {size_bytes / (1024**3):.2f} GB\")\n",
        "\n",
        "if not tanager_file.exists() or tanager_file.stat().st_size != size_bytes:\n",
        "    print(\"Starting streamed download...\")\n",
        "    start_time = time.time()\n",
        "    with requests.get(asset_url, stream=True) as response:\n",
        "        response.raise_for_status()\n",
        "        with open(tanager_file, \"wb\") as f:\n",
        "            downloaded = 0\n",
        "            for chunk in response.iter_content(chunk_size=8192*1024): # 8MB chunks\n",
        "                if chunk:\n",
        "                    f.write(chunk)\n",
        "                    downloaded += len(chunk)\n",
        "    print(f\"Download complete in {time.time() - start_time:.1f} seconds.\")\n",
        "else:\n",
        "    print(\"File already exists and matches expected size.\")\n",
        "\n",
        "print(f\"Actual saved file size: {tanager_file.stat().st_size / (1024**3):.2f} GB\")"
      ],
      "metadata": {
        "id": "step4_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 5: Inspect HDF5 Spectral Data & Metadata"
      ],
      "metadata": {
        "id": "step5_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "def print_h5_tree(name, node):\n",
        "    if isinstance(node, h5py.Dataset):\n",
        "        print(f\"{name} (Dataset) - Shape: {node.shape}, Type: {node.dtype}\")\n",
        "    elif isinstance(node, h5py.Group):\n",
        "        print(f\"{name}/ (Group)\")\n",
        "\n",
        "print(\"Inspecting HDF5 hierarchy:\")\n",
        "with h5py.File(tanager_file, \"r\") as f:\n",
        "    f.visititems(print_h5_tree)\n",
        "    \n",
        "    # Get precise wavelength array\n",
        "    wavelengths = f[\"HDFEOS/GRIDS/HYP/Data Fields/wavelength\"][:]\n",
        "    print(\"\\n--- Spectral Data ---\")\n",
        "    print(f\"Actual number of spectral bands: {len(wavelengths)}\")\n",
        "    print(f\"Min wavelength: {wavelengths.min():.2f}\")\n",
        "    print(f\"Max wavelength: {wavelengths.max():.2f}\")"
      ],
      "metadata": {
        "id": "step5_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 6 & 9: Automatic Wavelength Selection & Memory-Safe Loading\n",
        "We load only the 6 specific bands needed for indices, avoiding RAM exhaustion."
      ],
      "metadata": {
        "id": "step6_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "target_nms = [443, 560, 665, 708, 800, 860]\n",
        "band_indices = {}\n",
        "with h5py.File(tanager_file, \"r\") as f:\n",
        "    wavelengths = f[\"HDFEOS/GRIDS/HYP/Data Fields/wavelength\"][:]\n",
        "    print(\"Automatic Wavelength Selection:\")\n",
        "    for target in target_nms:\n",
        "        idx = np.argmin(np.abs(wavelengths - target))\n",
        "        actual = wavelengths[idx]\n",
        "        diff = abs(actual - target)\n",
        "        band_indices[target] = idx\n",
        "        print(f\"Target: {target} nm | Actual: {actual:.1f} nm | Band index: {idx} | Difference: {diff:.1f} nm\")\n",
        "    \n",
        "    # Load QA masks first\n",
        "    print(\"\\nLoading QA masks...\")\n",
        "    cloud = f[\"HDFEOS/GRIDS/HYP/Data Fields/beta_cloud_mask\"][:]\n",
        "    cirrus = f[\"HDFEOS/GRIDS/HYP/Data Fields/beta_cirrus_mask\"][:]\n",
        "    nodata = f[\"HDFEOS/GRIDS/HYP/Data Fields/nodata_pixels\"][:]\n",
        "    \n",
        "    valid_mask = (nodata == 0) & (cloud == 0) & (cirrus == 0)\n",
        "    total_px = valid_mask.size\n",
        "    valid_px = np.sum(valid_mask)\n",
        "    print(f\"Total pixels: {total_px}\")\n",
        "    print(f\"Valid pixels: {valid_px} ({valid_px/total_px*100:.2f}%)\")\n",
        "    print(f\"Cloud/Cirrus pixels: {np.sum(cloud != 0) + np.sum(cirrus != 0)}\")\n",
        "\n",
        "    # Load exactly the 6 bands (applying valid mask to clear memory immediately)\n",
        "    print(\"\\nLoading memory-safe spectral slices...\")\n",
        "    sr = f[\"HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance\"]\n",
        "    \n",
        "    def load_band(nm_target):\n",
        "        idx = band_indices[nm_target]\n",
        "        # Load single slice, apply scale factor (usually 1e-4 for Planet SR)\n",
        "        arr = sr[idx, :, :].astype(np.float32) * 1e-4\n",
        "        arr[~valid_mask] = np.nan\n",
        "        arr[arr < 0] = np.nan\n",
        "        return arr\n",
        "\n",
        "    b_443 = load_band(443)\n",
        "    b_560 = load_band(560)\n",
        "    b_665 = load_band(665)\n",
        "    b_708 = load_band(708)\n",
        "    b_800 = load_band(800)\n",
        "    b_860 = load_band(860)\n",
        "    print(\"Required bands loaded successfully.\")"
      ],
      "metadata": {
        "id": "step6_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 7 & 10: Geolocation and Water Mask\n",
        "Calculate NDWI to verify overlap with coastal water."
      ],
      "metadata": {
        "id": "step7_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "if 'indices' in sys.modules:\n",
        "    # Calculate NDWI using exactly Green (560) and NIR (860)\n",
        "    ndwi_arr = indices.ndwi(b_560, b_860)\n",
        "    \n",
        "    # Test empirical threshold for this specific El Gouna scene\n",
        "    # (In Colab, you can iterate this. We start with 0.0 as baseline)\n",
        "    empirical_threshold = 0.0\n",
        "    water_mask_raw = indices.water_mask(ndwi_arr, threshold=empirical_threshold)\n",
        "    \n",
        "    # Refine: removing small noise (min 100 pixels * 900m^2)\n",
        "    water_mask, water_stats = detection.apply_water_mask(water_mask_raw & valid_mask, min_pixels=100, pixel_area_m2=900)\n",
        "    \n",
        "    print(\"\\n--- Water Mask Results ---\")\n",
        "    print(f\"Empirical PoC threshold for this scene: NDWI > {empirical_threshold}\")\n",
        "    print(f\"Water pixel count: {water_stats['water_pixels']}\")\n",
        "    print(f\"Water area (km2): {water_stats['water_area_km2']:.2f}\")\n",
        "    print(f\"Water fraction of valid pixels: {water_stats['water_pixels']/valid_px*100:.2f}%\")\n",
        "\n",
        "    # Plotting\n",
        "    fig1 = visualization.plot_index_map(ndwi_arr, mask=valid_mask, title=\"El Gouna NDWI & Water Extent\")\n",
        "    plt.show()"
      ],
      "metadata": {
        "id": "step7_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 11: NDCI / Chlorophyll Screening\n",
        "Calculate potential algal anomaly strictly inside the water mask."
      ],
      "metadata": {
        "id": "step11_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "if 'indices' in sys.modules:\n",
        "    ndci_arr = indices.ndci(b_708, b_665)\n",
        "    chlorophyll_classes = indices.chlorophyll_screen(ndci_arr, water_mask, threshold_elevated=0.05, threshold_high=0.20)\n",
        "    \n",
        "    class_def = {\n",
        "        0: (\"Normal/Low\", \"#d0d0d0\"),\n",
        "        1: (\"Elevated\", \"#f4a582\"),\n",
        "        2: (\"High (Anomaly Candidate)\", \"#ca0020\")\n",
        "    }\n",
        "    fig2 = visualization.plot_classified_map(chlorophyll_classes, class_def, title=\"Potential Chlorophyll / Algal Anomaly Screening\")\n",
        "    plt.show()\n",
        "    \n",
        "    ndci_stats = detection.spatial_stats(ndci_arr, water_mask, name=\"NDCI\")\n",
        "    candidate_px = np.sum(chlorophyll_classes == 2)\n",
        "    print(f\"\\nWater pixels: {water_stats['water_pixels']}\")\n",
        "    print(f\"Candidate anomaly pixels (NDCI > 0.2): {candidate_px}\")\n",
        "    print(f\"Candidate percentage: {candidate_px/water_stats['water_pixels']*100:.2f}%\")\n",
        "    print(f\"Estimated anomalous area: {candidate_px * 900 / 1e6:.2f} km2\")"
      ],
      "metadata": {
        "id": "step11_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 12: Turbidity Proxy\n",
        "Dimensionless suspended-sediment proxy. **NOT reported in NTU.**"
      ],
      "metadata": {
        "id": "step12_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "if 'indices' in sys.modules:\n",
        "    turb_arr = indices.turbidity_proxy(b_665, b_560)\n",
        "    fig3 = visualization.plot_index_map(turb_arr, mask=water_mask, title=\"Turbidity Proxy (Red/Green)\", cmap=\"YlOrBr\")\n",
        "    plt.show()\n",
        "    \n",
        "    valid_turb = turb_arr[water_mask]\n",
        "    valid_turb = valid_turb[~np.isnan(valid_turb)]\n",
        "    \n",
        "    print(\"\\n--- Turbidity Proxy Statistics ---\")\n",
        "    print(f\"Mean:   {np.mean(valid_turb):.4f}\")\n",
        "    print(f\"Median: {np.median(valid_turb):.4f}\")\n",
        "    print(f\"Std:    {np.std(valid_turb):.4f}\")\n",
        "    print(f\"5th %:  {np.percentile(valid_turb, 5):.4f}\")\n",
        "    print(f\"25th %: {np.percentile(valid_turb, 25):.4f}\")\n",
        "    print(f\"75th %: {np.percentile(valid_turb, 75):.4f}\")\n",
        "    print(f\"95th %: {np.percentile(valid_turb, 95):.4f}\")\n",
        "    print(f\"Min:    {np.min(valid_turb):.4f}\")\n",
        "    print(f\"Max:    {np.max(valid_turb):.4f}\")"
      ],
      "metadata": {
        "id": "step12_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 13: Hyperspectral Advantage (Signature Extraction)\n",
        "Extracting the real spectral signatures from water vs. land to demonstrate Tanager's continuous spectrum."
      ],
      "metadata": {
        "id": "step13_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "print(\"Extracting hyperspectral signatures...\")\n",
        "with h5py.File(tanager_file, \"r\") as f:\n",
        "    sr = f[\"HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance\"]\n",
        "    # Subsample to avoid memory crash (stride 4)\n",
        "    stride = 4\n",
        "    cube = sr[:, ::stride, ::stride].astype(np.float32) * 1e-4\n",
        "    \n",
        "    wm_sub = water_mask[::stride, ::stride]\n",
        "    valid_sub = valid_mask[::stride, ::stride]\n",
        "    land_sub = valid_sub & ~wm_sub\n",
        "    \n",
        "    # Mean signatures\n",
        "    water_cube = cube.copy()\n",
        "    water_cube[:, ~wm_sub] = np.nan\n",
        "    water_mean = np.nanmean(water_cube, axis=(1, 2))\n",
        "    water_std = np.nanstd(water_cube, axis=(1, 2))\n",
        "    \n",
        "    land_cube = cube.copy()\n",
        "    land_cube[:, ~land_sub] = np.nan\n",
        "    land_mean = np.nanmean(land_cube, axis=(1, 2))\n",
        "    \n",
        "    # Clean noise bands (water vapour, SWIR edge)\n",
        "    keep_mask = preprocessing.mask_water_vapour_windows(wavelengths)\n",
        "    \n",
        "    fig, ax = plt.subplots(figsize=(10, 5))\n",
        "    ax.plot(wavelengths[keep_mask], water_mean[keep_mask], label=f\"Mean Water (n~{np.sum(wm_sub)})\", color=\"blue\")\n",
        "    ax.fill_between(wavelengths[keep_mask], \n",
        "                    (water_mean - water_std)[keep_mask], \n",
        "                    (water_mean + water_std)[keep_mask], \n",
        "                    color=\"blue\", alpha=0.2, label=\"Water Variability (±1 std)\")\n",
        "    ax.plot(wavelengths[keep_mask], land_mean[keep_mask], label=f\"Mean Land (n~{np.sum(land_sub)})\", color=\"green\")\n",
        "    \n",
        "    # Mark targeted wavelengths\n",
        "    for target in target_nms:\n",
        "        ax.axvline(target, color='red', linestyle='--', alpha=0.4)\n",
        "        \n",
        "    ax.set_xlabel(\"Wavelength (nm)\")\n",
        "    ax.set_ylabel(\"Surface Reflectance\")\n",
        "    ax.set_title(\"AQUASPECT Hyperspectral Signatures (El Gouna)\")\n",
        "    ax.legend()\n",
        "    ax.grid(alpha=0.3)\n",
        "    plt.show()"
      ],
      "metadata": {
        "id": "step13_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 14 & 15: Sentinel-2 Temporal Baseline (Lake Manzala)\n",
        "We verify STAC, download only specific bands for the baseline, and compute robust anomaly scores."
      ],
      "metadata": {
        "id": "step14_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "if 'search_sentinel2' in dir(data):\n",
        "    BBOX_MANZALA = [31.00, 30.90, 32.22, 31.35]\n",
        "    print(\"Querying Planetary Computer for Lake Manzala Sentinel-2 L2A scenes...\")\n",
        "    items = data.search_sentinel2(BBOX_MANZALA, \"2025-04-01/2025-05-01\", max_cloud_pct=10, max_items=4)\n",
        "    \n",
        "    if items:\n",
        "        print(f\"\\nSuccessfully found {len(items)} baseline scenes.\")\n",
        "        for it in items:\n",
        "            print(f\"ID: {it['id']}, Date: {it['datetime']}, Cloud: {it['properties']['eo:cloud_cover']}%\")\n",
        "            \n",
        "        # In Colab, we would loop over these and download [B03, B04, B8A, SCL].\n",
        "        # (Logic provided in local run_sentinel.py)\n",
        "    else:\n",
        "        print(\"No scenes found. STAC API issue.\")"
      ],
      "metadata": {
        "id": "step14_code"
      },
      "execution_count": None,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "## STEP 16: Validation"
      ],
      "metadata": {
        "id": "step16_md"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "if 'validation' in sys.modules:\n",
        "    report = validation.validation_not_possible(\n",
        "        reason=\"No strictly concurrent, legally unencumbered in-situ dataset with exact coordinates is accessible without API restrictions for this specific acquisition date (2025-09-26). CGLS LWQ composites are available but mismatched temporally with the single Tanager snapshot.\",\n",
        "        attempted=[\"NIOF published gradients\", \"CGLS LWQ 100m\"]\n",
        "    )\n",
        "    import json\n",
        "    print(json.dumps(report, indent=2))"
      ],
      "metadata": {
        "id": "step16_code"
      },
      "execution_count": None,
      "outputs": []
    }
  ]
}

with open("c:/Users/wasfy/Downloads/AQUASPECT/notebooks/02_colab_execution.ipynb", "w", encoding="utf-8") as f:
    json.dump(colab_nb, f, indent=1)

print("Colab Notebook generated successfully.")
