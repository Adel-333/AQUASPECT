"""
Build a Colab-ready notebook.
Images are displayed via plt.imshow inside code cells so they are embedded
as proper PNG outputs when the notebook is executed locally.
The resulting .ipynb can be opened in Colab and every figure is already visible.
"""
import nbformat as nbf
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("c:/Users/wasfy/Downloads/AQUASPECT")
MAPS    = PROJECT_ROOT / "results" / "maps"
FIGS    = PROJECT_ROOT / "results" / "figures"
NB_OUT  = PROJECT_ROOT / "notebooks" / "03_aquaspect_colab.ipynb"

nb  = nbf.v4.new_notebook()
cells = []

# ── Title ─────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""\
# AQUASPECT — Proof of Concept
**Arab Youth Space Hackathon 813 · Theme 6: Water Quality & Inland/Coastal Water Intelligence**

> **Validation note:** No concurrent in-situ measurements are available for these scenes.
> All indices are dimensionless proxies. Anomalies are statistical deviations from a
> 12-month historical baseline — not confirmed pollution or algal bloom events.

---
"""))

# ── Setup (Colab-aware paths) ─────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""\
## Setup
Run this cell first. If you are on **Google Colab**, mount your Drive and set `PROJECT_ROOT`
to wherever you uploaded the AQUASPECT folder (e.g. `/content/drive/MyDrive/AQUASPECT`).
"""))

cells.append(nbf.v4.new_code_cell("""\
import os, sys, warnings
import numpy as np
import pandas as pd
import h5py
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
warnings.filterwarnings('ignore')

# ── Set project root ──────────────────────────────────────────────────────────
# On Google Colab: mount Drive first, then set this to your uploaded folder:
#   from google.colab import drive; drive.mount('/content/drive')
#   PROJECT_ROOT = "/content/drive/MyDrive/AQUASPECT"

# Local path (used for execution):
PROJECT_ROOT = r"c:/Users/wasfy/Downloads/AQUASPECT"

import pathlib
PROJECT_ROOT  = pathlib.Path(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aquaspect import preprocessing, indices, detection

DATA_DIR     = PROJECT_ROOT / "data" / "sample_input"
RESULTS_MAPS = PROJECT_ROOT / "results" / "maps"
RESULTS_FIGS = PROJECT_ROOT / "results" / "figures"
RESULTS_TBLS = PROJECT_ROOT / "results" / "tables"

print("Project root:", PROJECT_ROOT)
print("Maps dir exists:", RESULTS_MAPS.exists())
print("Figures dir exists:", RESULTS_FIGS.exists())
"""))

# ── helper function cell ───────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell("""\
def show_map(path, title="", figsize=(12, 8)):
    img = mpimg.imread(str(path))
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(img)
    ax.axis('off')
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    plt.tight_layout()
    plt.show()
"""))

# ── Part 1 ────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""\
---
## Part 1 — El Gouna Hyperspectral Analysis (Planet Tanager)
**Scene:** `20250926_092059_95_4001` · **Date:** 2025-09-26  
**Sensor:** Planet Tanager · **Bands:** 426 · **Range:** 376–2499 nm · **GSD:** ~33 m
"""))

cells.append(nbf.v4.new_code_cell("""\
TANAGER_FILE = DATA_DIR / "20250926_092059_95_4001_ortho_sr_hdf5.h5"

valid_mask, qa_stats = preprocessing.build_qa_mask(str(TANAGER_FILE))
print("QA Statistics:")
for k, v in qa_stats.items():
    print(f"  {k}: {v}")

with h5py.File(TANAGER_FILE, "r") as f:
    sr          = f["HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance"]
    wavelengths = sr.attrs["wavelengths"][:]
    print(f"\\nArray shape : {sr.shape}")
    print(f"Wavelength  : {wavelengths[0]:.1f} – {wavelengths[-1]:.1f} nm")

    target_nms = [443, 560, 665, 708, 800, 860]
    band_idx   = {t: int(np.argmin(np.abs(wavelengths - t))) for t in target_nms}
    for t, i in band_idx.items():
        print(f"  {t} nm  ->  {wavelengths[i]:.1f} nm  (band {i})")

    def load_b(nm):
        arr = sr[band_idx[nm], :, :].astype(np.float32) * 1e-4
        arr[~valid_mask] = np.nan
        arr[(arr < 0) | (arr > 1)] = np.nan
        return arr

    b_green, b_red, b_rededge, b_nir2 = (
        load_b(560), load_b(665), load_b(708), load_b(860)
    )

ndwi_arr = indices.ndwi(b_green, b_nir2)
wm_raw   = indices.water_mask(ndwi_arr, threshold=0.0)
water_mask, ws = detection.apply_water_mask(wm_raw & valid_mask,
                                             min_pixels=100, pixel_area_m2=900)
print(f"\\nWater area   : {ws['estimated_area_km2']:.2f} km²")
print(f"Water pixels : {ws['retained_water_pixels']:,}")

ndci_arr = indices.ndci(b_rededge, b_red)
turb_arr = indices.turbidity_proxy(b_red, b_green)
tv = turb_arr[water_mask]; tv = tv[~np.isnan(tv)]
print(f"Turbidity proxy (dimensionless): mean={np.mean(tv):.4f}  max={np.max(tv):.4f}")
"""))

# image cells
cells.append(nbf.v4.new_code_cell(
    f'show_map(RESULTS_MAPS / "elgouna_water_mask.png",\n'
    f'         "Map 1 — Water Mask (NDWI threshold = 0.0)")\n'
))
cells.append(nbf.v4.new_code_cell(
    f'show_map(RESULTS_MAPS / "elgouna_chlorophyll_screening.png",\n'
    f'         "Map 2 — NDCI Chlorophyll Screening")\n'
))
cells.append(nbf.v4.new_code_cell(
    f'show_map(RESULTS_MAPS / "elgouna_turbidity_proxy.png",\n'
    f'         "Map 3 — Turbidity Proxy (Red/Green Ratio)")\n'
))
cells.append(nbf.v4.new_code_cell(
    f'show_map(RESULTS_FIGS / "elgouna_hyperspectral_signature.png",\n'
    f'         "Figure 1 — Hyperspectral Spectral Signature (426 bands, 376–2499 nm)", figsize=(14, 5))\n'
))

# ── Part 2 ────────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""\
---
## Part 2 — Lake Manzala Temporal Baseline (Sentinel-2 L2A)
8 distinct scenes · June 2024 – May 2025 · Turbidity proxy Z-score anomaly detection
"""))

cells.append(nbf.v4.new_code_cell("""\
s2_metrics = pd.read_csv(RESULTS_TBLS / "manzala_temporal_metrics.csv")
print("12-Month Scene Table:")
display(s2_metrics)
"""))

cells.append(nbf.v4.new_code_cell(
    f'show_map(RESULTS_FIGS / "manzala_temporal_baseline.png",\n'
    f'         "Figure 2 — 12-Month Turbidity Proxy Baseline (Sentinel-2 L2A)", figsize=(14, 7))\n'
))

cells.append(nbf.v4.new_code_cell("""\
anomaly = pd.read_csv(RESULTS_TBLS / "manzala_anomaly_summary.csv")
total_water = s2_metrics.iloc[-1]['water_pixels']
extreme_px  = anomaly.iloc[0]['anomaly_extreme_px']

print("Anomaly Detection Results (Z-Score method):")
display(anomaly)

print(f"\\nOn {anomaly.iloc[0]['reference_date']}:")
print(f"  {extreme_px:,} pixels ({extreme_px/total_water:.1%}) exceed Z = 3.0 vs 12-month baseline.")
print("  => Statistically extreme deviation. Requires field verification.")
"""))

# ── Write ─────────────────────────────────────────────────────────────────────
nb.cells = cells
with open(NB_OUT, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"Colab notebook written: {NB_OUT}")

# ── Execute locally to pre-embed all outputs ──────────────────────────────────
executed = PROJECT_ROOT / "notebooks" / "03_aquaspect_colab_executed.ipynb"
result = subprocess.run(
    [sys.executable, "-m", "jupyter", "nbconvert",
     "--to", "notebook", "--execute",
     str(NB_OUT),
     "--output", "03_aquaspect_colab_executed.ipynb"],
    cwd=str(PROJECT_ROOT / "notebooks"),
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("ERRORS:", result.stderr[-2000:])
else:
    print(f"Executed notebook: {executed}")
    print(f"Size: {executed.stat().st_size / 1024:.0f} KB")
