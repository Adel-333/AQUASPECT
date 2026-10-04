import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Ensure src/ is on path
PROJECT_ROOT = Path("c:/Users/wasfy/Downloads/AQUASPECT")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aquaspect import config, preprocessing, indices, detection, visualization
from aquaspect.data import search_sentinel2, download_s2_band, load_raster_clip

DATA_DIR = PROJECT_ROOT / "data" / "sample_input"
RESULTS_MAPS = PROJECT_ROOT / "results" / "maps"
RESULTS_FIGURES = PROJECT_ROOT / "results" / "figures"
RESULTS_TABLES = PROJECT_ROOT / "results" / "tables"

BBOX_MANZALA = [31.00, 30.90, 32.22, 31.35]

def run_sentinel():
    print("=== SENTINEL-2 LAKE MANZALA ===")
    # 1. Search for a few scenes to build a baseline (limit to 5 to save time)
    # Using early 2025 as a time window, or late 2023/2024. Let's use early 2025.
    print("Searching Planetary Computer...")
    items = search_sentinel2(
        bbox=BBOX_MANZALA, 
        date_range="2025-01-01/2025-05-01", 
        max_cloud_pct=10, 
        max_items=4
    )
    
    if not items:
        print("No items found or pystac failure.")
        return
        
    dates = []
    ndwi_means = []
    turbidity_means = []
    
    # Store baseline stack (we will just compute turbidity proxy stack for anomaly)
    turbidity_stack = []
    
    for item in items:
        print(f"Processing scene {item['id']} ({item['datetime']})")
        b3_path = download_s2_band(item, "B03", DATA_DIR, sign=True)
        b4_path = download_s2_band(item, "B04", DATA_DIR, sign=True)
        b8a_path = download_s2_band(item, "B8A", DATA_DIR, sign=True)
        scl_path = download_s2_band(item, "SCL", DATA_DIR, sign=True)
        
        # Load clipped raster arrays
        b3, _, _ = load_raster_clip(b3_path, BBOX_MANZALA, target_crs="EPSG:32636")
        b4, _, _ = load_raster_clip(b4_path, BBOX_MANZALA, target_crs="EPSG:32636")
        b8a, _, _ = load_raster_clip(b8a_path, BBOX_MANZALA, target_crs="EPSG:32636")
        scl, transform, meta = load_raster_clip(scl_path, BBOX_MANZALA, target_crs="EPSG:32636")
        
        # Scale to reflectance (S2 L2A BOA is scaled by 10000)
        b3 = (b3 / 10000.0).astype(np.float32)
        b4 = (b4 / 10000.0).astype(np.float32)
        b8a = (b8a / 10000.0).astype(np.float32)
        
        # Valid mask (SCL 6 is water, but we'll accept 4 (veg), 5 (bare), 6 (water), 7 (unclass) to allow NDWI to do its job)
        valid = (scl == 4) | (scl == 5) | (scl == 6) | (scl == 7)
        b3[~valid] = np.nan
        b4[~valid] = np.nan
        b8a[~valid] = np.nan
        
        # NDWI & Turbidity Proxy
        ndwi = indices.ndwi(b3, b8a)
        turbidity = indices.turbidity_proxy(b4, b3)
        
        water_mask_raw = indices.water_mask(ndwi, threshold=0.1)
        water_mask, _ = detection.apply_water_mask(water_mask_raw & valid, min_pixels=100, pixel_area_m2=100) # 10m res
        
        stats_ndwi = detection.spatial_stats(ndwi, water_mask, name="NDWI")
        stats_turb = detection.spatial_stats(turbidity, water_mask, name="Turbidity")
        
        if stats_ndwi["NDWI_count"] > 0:
            dates.append(item['datetime'].split("T")[0])
            ndwi_means.append(stats_ndwi["NDWI_mean"])
            turbidity_means.append(stats_turb["Turbidity_mean"])
            
            # Prepare stack for baseline (we'll just use turbidity for the anomaly detection demo)
            turbidity_obs = turbidity.copy()
            turbidity_obs[~water_mask] = np.nan
            turbidity_stack.append(turbidity_obs)
            
            last_water_mask = water_mask
            last_turbidity = turbidity_obs
            
    # Baseline computation
    if len(turbidity_stack) > 1:
        base_mean, base_std = detection.build_baseline(turbidity_stack, robust=True)
        
        # Compute anomaly for the last observation
        z_map, anomaly_class, anomaly_summary = detection.detect_anomalies(
            last_turbidity, base_mean, base_std, last_water_mask
        )
        print("Anomaly Summary for last observation:", anomaly_summary)
        
        # Plot Time series
        visualization.plot_time_series(
            dates, turbidity_means, 
            baseline_mean=float(np.mean(turbidity_means)), 
            baseline_std=float(np.std(turbidity_means)),
            ylabel="Turbidity Proxy (Red/Green)",
            title="Lake Manzala Turbidity Proxy Time Series",
            save_path=RESULTS_FIGURES / "manzala_temporal_baseline.png"
        )
        
        # Save metrics
        df = pd.DataFrame({"Date": dates, "Mean_NDWI": ndwi_means, "Mean_Turbidity_Proxy": turbidity_means})
        df.to_csv(RESULTS_TABLES / "manzala_temporal_metrics.csv", index=False)
        print("Sentinel-2 processing complete.")

if __name__ == "__main__":
    run_sentinel()
