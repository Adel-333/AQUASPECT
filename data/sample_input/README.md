# Data Directory

## Structure

```
data/
└── sample_input/
    ├── README.md          ← this file
    ├── download_data.py   ← deterministic download script
    └── scene_manifest.json ← exact scene IDs, dates, URLs
```

## What goes here

This directory contains **only**:

1. A deterministic download script that fetches the exact scenes used in the analysis.
2. A scene manifest (JSON) recording every scene ID, acquisition date, bounding box, and source URL.
3. Small permitted sample clips (if the licence allows redistribution).

## What does NOT go here

- Full Sentinel-2 scenes (hundreds of MB each)
- Full Tanager HDF5 files (multi-GB)
- Any restricted or commercially licensed imagery
- API keys or credentials

## How to acquire the data

Run the download script from the project root:

```bash
python data/sample_input/download_data.py
```

The script will:
1. Read `scene_manifest.json` for exact scene IDs and date ranges.
2. Search Microsoft Planetary Computer STAC for Sentinel-2 scenes.
3. Download only the bands needed for the analysis (B03, B04, B8A, SCL).
4. Download the CGLS LWQ validation product for the matching date.
5. Save everything to `data/sample_input/`.

**Credentials required:**
- Set `PC_SDK_SUBSCRIPTION_KEY` in a `.env` file at the project root
  for authenticated Planetary Computer access (free, register at
  https://planetarycomputer.microsoft.com/).
- For Tanager data, set `PLANET_API_KEY` in the same `.env` file.

## AOI — Lake Manzala, Egypt

**Bounding box (EPSG:4326):** `[31.00, 30.90, 32.22, 31.35]`

**Why Lake Manzala:**
- Egypt's largest coastal lagoon (~572 km² current extent)
- Classified as hypereutrophic; documented harmful algal blooms (HABs)
- Receives wastewater from multiple Nile Delta drains (Bahr Al-Baqar,
  Hadous, El-Serw, Serw)
- Published in-situ WQI measurements available (NIOF, 2021–2023)
- CGLS LWQ 100m product available as external benchmark
- Full Sentinel-2 L2A temporal coverage (~5-day revisit)
- Strong optical signal contrast between polluted south and cleaner north

**Target CRS:** EPSG:32636 (UTM Zone 36N) — appropriate for the Nile Delta region.
