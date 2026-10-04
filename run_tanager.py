import os
import sys
import numpy as np
import h5py
import requests
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure src/ is on path
PROJECT_ROOT = Path("c:/Users/wasfy/Downloads/AQUASPECT")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aquaspect import config, preprocessing, indices, detection, visualization

DATA_DIR = PROJECT_ROOT / "data" / "sample_input"
RESULTS_MAPS = PROJECT_ROOT / "results" / "maps"
RESULTS_FIGURES = PROJECT_ROOT / "results" / "figures"
RESULTS_TABLES = PROJECT_ROOT / "results" / "tables"

TANAGER_URL = "https://storage.googleapis.com/open-cogs/planet-stac/tanager1-release2-core-imagery/ortho_sr_hdf5/20250926_092059_95_4001_ortho_sr_hdf5.h5"
TANAGER_FILE = DATA_DIR / "20250926_092059_95_4001_ortho_sr_hdf5.h5"

def download_file(url, dest):
    if dest.exists():
        print(f"Already downloaded: {dest.name}")
        return
    print(f"Downloading {url} to {dest}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192*1024):
                if chunk: f.write(chunk)
    print("Download complete.")

def run_tanager():
    print("=== TANAGER EL GOUNA SCENE ===")
    download_file(TANAGER_URL, TANAGER_FILE)
    
    # 1. Quality mask
    valid_mask, qa_stats = preprocessing.build_qa_mask(str(TANAGER_FILE))
    
    # Save scene summary
    pd.DataFrame([qa_stats]).to_csv(RESULTS_TABLES / "elgouna_scene_summary.csv", index=False)
    
    # 2. Extract wavelengths and load bands
    # We load only the required bands into memory to save RAM
    with h5py.File(TANAGER_FILE, "r") as f:
        # get wavelengths
        wavelengths = f["HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance"].attrs["wavelengths"][:]
        
        target_nms = [443, 560, 665, 708, 800, 860]
        band_indices = {}
        for target in target_nms:
            idx = np.argmin(np.abs(wavelengths - target))
            band_indices[target] = (idx, wavelengths[idx])
            print(f"Target {target} nm -> Band {idx} ({wavelengths[idx]:.1f} nm)")
            
        sr = f["HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance"]
        
        # Load bands (Tanager order is bands, rows, cols)
        def load_b(nm):
            idx = band_indices[nm][0]
            arr = sr[idx, :, :].astype(np.float32) * 1e-4
            arr[~valid_mask] = np.nan
            arr[arr < 0] = np.nan
            arr[arr > 1] = np.nan
            return arr
            
        b_green = load_b(560)
        b_red = load_b(665)
        b_rededge = load_b(708)
        b_nir = load_b(800)
        b_nir2 = load_b(860)
        b_blue = load_b(443)

    # 3. Water Mask
    ndwi_arr = indices.ndwi(b_green, b_nir2)
    # empirical threshold 0.0
    water_mask_raw = indices.water_mask(ndwi_arr, threshold=0.0)
    # Refine (remove small components) - Tanager is 30m, 900m^2 per pixel
    water_mask, water_stats = detection.apply_water_mask(water_mask_raw & valid_mask, min_pixels=100, pixel_area_m2=900)
    
    print(f"Water stats: {water_stats}")
    
    visualization.plot_index_map(ndwi_arr, mask=valid_mask, title="El Gouna NDWI", cmap="Blues", save_path=RESULTS_MAPS/"elgouna_water_mask.png")
    
    # 4. Chlorophyll Screening
    ndci_arr = indices.ndci(b_rededge, b_red)
    chlorophyll_classes = indices.chlorophyll_screen(ndci_arr, water_mask, threshold_elevated=0.05, threshold_high=0.20)
    
    class_def = {
        0: ("Normal/Low", "#d0d0d0"),
        1: ("Elevated", "#f4a582"),
        2: ("High (Anomaly Candidate)", "#ca0020")
    }
    visualization.plot_classified_map(chlorophyll_classes, class_def, title="Potential Chlorophyll Anomaly Screening", save_path=RESULTS_MAPS/"elgouna_chlorophyll_screening.png")
    
    ndci_stats = detection.spatial_stats(ndci_arr, water_mask, name="NDCI")
    pd.DataFrame([ndci_stats]).to_csv(RESULTS_TABLES / "elgouna_chlorophyll_summary.csv", index=False)
    
    # 5. Turbidity Proxy
    turb_arr = indices.turbidity_proxy(b_red, b_green)
    visualization.plot_index_map(turb_arr, mask=water_mask, title="Turbidity Proxy (Red/Green)", cmap="YlOrBr", save_path=RESULTS_MAPS/"elgouna_turbidity_proxy.png")
    
    # Turbidity statistics
    valid_turb = turb_arr[water_mask]
    valid_turb = valid_turb[~np.isnan(valid_turb)]
    turb_stats = {
        "count": len(valid_turb),
        "mean": float(np.mean(valid_turb)),
        "median": float(np.median(valid_turb)),
        "std": float(np.std(valid_turb)),
        "p5": float(np.percentile(valid_turb, 5)),
        "p25": float(np.percentile(valid_turb, 25)),
        "p75": float(np.percentile(valid_turb, 75)),
        "p95": float(np.percentile(valid_turb, 95)),
        "min": float(np.min(valid_turb)),
        "max": float(np.max(valid_turb)),
    }
    print(f"Turbidity Proxy stats (Red/Green ratio, dimensionless — NOT NTU):")
    for k, v in turb_stats.items():
        print(f"  {k}: {v:.5f}" if isinstance(v, float) else f"  {k}: {v}")
    pd.DataFrame([turb_stats]).to_csv(RESULTS_TABLES / "elgouna_turbidity_summary.csv", index=False)
    
    # 6. Hyperspectral Signature
    print("Extracting mean hyperspectral signatures...")
    with h5py.File(TANAGER_FILE, "r") as f:
        sr = f["HDFEOS/GRIDS/HYP/Data Fields/surface_reflectance"]
        # Subsample to avoid memory issues (stride 4)
        stride = 4
        cube = sr[:, ::stride, ::stride].astype(np.float32) * 1e-4
        
        wm_sub = water_mask[::stride, ::stride]
        valid_sub = valid_mask[::stride, ::stride]
        
        # Land mask (valid but not water)
        land_sub = valid_sub & ~wm_sub
        
        # Mean signatures
        water_cube = cube.copy()
        water_cube[:, ~wm_sub] = np.nan
        water_mean = np.nanmean(water_cube, axis=(1, 2))
        
        land_cube = cube.copy()
        land_cube[:, ~land_sub] = np.nan
        land_mean = np.nanmean(land_cube, axis=(1, 2))
        
        # Plot
        keep_mask = preprocessing.mask_water_vapour_windows(wavelengths)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(wavelengths[keep_mask], water_mean[keep_mask], label=f"Water (n~{np.sum(wm_sub)})", color="blue")
        ax.plot(wavelengths[keep_mask], land_mean[keep_mask], label=f"Land/Veg (n~{np.sum(land_sub)})", color="green")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Surface Reflectance")
        ax.set_title("Hyperspectral Signatures (El Gouna)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(RESULTS_FIGURES / "elgouna_hyperspectral_signature.png", dpi=150)
        plt.close(fig)

    print("Tanager processing complete.\n")

if __name__ == "__main__":
    run_tanager()
