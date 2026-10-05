# Data Directory

## Structure

```
data/
└── sample_input/
    ├── README.md               <- this file
    ├── download_data.py        <- Sentinel-2 download utility
    ├── manzala_candidate_scenes.csv <- 40 candidate cloud-free scenes discovered via STAC
    └── scene_manifest.json     <- verified scene IDs, dates, and bounding boxes
```

## What goes here

This directory contains:

1. Scene manifest (`scene_manifest.json`) recording the verified Tanager and Sentinel-2 scene IDs and coordinates.
2. The candidate scene catalog discovered for Lake Manzala.
3. Download scripts to retrieve specific spectral bands.

## What does NOT go here

- Full Tanager HDF5 cubes (~1.08 GB) - kept locally / excluded via `.gitignore`.
- Full raw Sentinel-2 SAFE archives.
- API keys, tokens, or private credentials.

## AOI 1: Lake Manzala, Egypt (Temporal Baseline AOI)

- Bounding box (EPSG:4326): `[31.00°E, 30.90°N, 32.22°E, 31.35°N]`
- Target CRS: EPSG:32636 (UTM Zone 36N)
- Characteristics: Egypt's largest coastal lagoon (~572 km²), hypereutrophic, receives drainage from agricultural/urban canals.

## AOI 2: El Gouna, Red Sea, Egypt (Hyperspectral Characterization AOI)

- Bounding box (EPSG:4326): `[33.511°E, 27.334°N, 33.758°E, 27.565°N]`
- Scene ID: `20250926_092059_95_4001` (Acquired 2025-09-26)
- Characteristics: Marine and coastal waters analyzed across 426 contiguous spectral bands (376-2499 nm).
