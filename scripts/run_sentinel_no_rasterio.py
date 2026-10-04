import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
import json

# Ensure src/ is on path
PROJECT_ROOT = Path("c:/Users/wasfy/Downloads/AQUASPECT")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aquaspect import indices, detection, visualization

DATA_DIR = PROJECT_ROOT / "data" / "sample_input"
RESULTS_FIGURES = PROJECT_ROOT / "results" / "figures"
RESULTS_TABLES = PROJECT_ROOT / "results" / "tables"

BBOX_MANZALA = [31.00, 30.90, 32.22, 31.35]

try:
    import tifffile
    HAS_TIFFFILE = True
    print("tifffile available")
except ImportError:
    HAS_TIFFFILE = False
    print("tifffile not available")


def sign_url(href):
    r = requests.get(f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={href}")
    if r.status_code == 200 and r.text.strip():
        return r.json()["href"]
    return href  # fallback: try unsigned


def dl(item_id, href, name):
    dest = DATA_DIR / f"{item_id}_{name}.tif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    print(f"  Downloading {name}...")
    signed = sign_url(href)
    with requests.get(signed, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    return dest


def load_tif(path):
    """Load a GeoTIFF using tifffile (handles COG/BigTIFF)."""
    arr = tifffile.imread(str(path))
    return arr.astype(np.float32)


def run_sentinel():
    print("=== SENTINEL-2 LAKE MANZALA ===")

    url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": BBOX_MANZALA,
        "datetime": "2025-04-01/2025-05-01",
        "query": {"eo:cloud_cover": {"lt": 10}},
        "limit": 3,
    }
    r = requests.post(url, json=payload)
    items = r.json().get("features", [])
    if not items:
        print("No items found.")
        return

    print(f"Found {len(items)} scenes.")

    dates = []
    ndwi_means = []
    turb_means = []
    turb_stack = []
    last_water_mask = None
    last_turbidity = None

    for item in items:
        date_str = item["properties"]["datetime"].split("T")[0]
        iid = item["id"]
        cloud_pct = item["properties"].get("eo:cloud_cover", "?")
        print(f"\nScene: {iid} | Date: {date_str} | Cloud: {cloud_pct}%")

        try:
            b3_path = dl(iid, item["assets"]["B03"]["href"], "B03")
            b4_path = dl(iid, item["assets"]["B04"]["href"], "B04")
            b8a_path = dl(iid, item["assets"]["B8A"]["href"], "B8A")
            scl_path = dl(iid, item["assets"]["SCL"]["href"], "SCL")

            # Sentinel-2 L2A bands: 10980x10980 at 10m, 5490x5490 at 20m
            # Subsample stride=10 → effective 100m to keep memory sane
            stride_10m = 10   # 10m bands → 100m
            stride_20m = 5    # 20m bands → 100m

            b3  = load_tif(b3_path )[::stride_10m, ::stride_10m] / 10000.0
            b4  = load_tif(b4_path )[::stride_10m, ::stride_10m] / 10000.0
            b8a = load_tif(b8a_path)[::stride_20m, ::stride_20m] / 10000.0
            scl = load_tif(scl_path)[::stride_20m, ::stride_20m]

            # Align shapes (SCL/B8A at 5490//5 = 1098; B03 at 10980//10 = 1098)
            ny = min(b3.shape[0], b8a.shape[0], scl.shape[0])
            nx = min(b3.shape[1], b8a.shape[1], scl.shape[1])
            b3  = b3[:ny, :nx]
            b4  = b4[:ny, :nx]
            b8a = b8a[:ny, :nx]
            scl = scl[:ny, :nx]

            # SCL valid: 4=vegetation, 5=bare, 6=water, 7=unclassified
            valid = np.isin(scl.astype(int), [4, 5, 6, 7])
            b3[~valid] = np.nan
            b4[~valid] = np.nan
            b8a[~valid] = np.nan

            ndwi_arr = indices.ndwi(b3, b8a)
            turb_arr = indices.turbidity_proxy(b4, b3)

            wm_raw = indices.water_mask(ndwi_arr, threshold=0.1)
            wm, _ = detection.apply_water_mask(wm_raw & valid, min_pixels=10, pixel_area_m2=10000)

            stats_ndwi = detection.spatial_stats(ndwi_arr, wm, name="NDWI")
            stats_turb = detection.spatial_stats(turb_arr, wm, name="Turbidity")

            if stats_ndwi["NDWI_count"] > 0:
                dates.append(date_str)
                ndwi_means.append(stats_ndwi["NDWI_mean"])
                turb_means.append(stats_turb["Turbidity_mean"])
                t_obs = turb_arr.copy()
                t_obs[~wm] = np.nan
                turb_stack.append(t_obs)
                last_water_mask = wm
                last_turbidity = t_obs
                print(f"  Water pixels: {stats_ndwi['NDWI_count']:,} | Mean NDWI: {stats_ndwi['NDWI_mean']:.4f} | Mean Turb: {stats_turb['Turbidity_mean']:.4f}")
            else:
                print("  No usable water pixels found for this scene.")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    if len(turb_stack) < 2:
        print(f"\nOnly {len(turb_stack)} usable scene(s) — cannot build a multi-scene temporal baseline.")
        if len(turb_stack) == 1:
            df = pd.DataFrame({"Date": dates, "Mean_NDWI": ndwi_means, "Mean_Turbidity_Proxy": turb_means})
            df.to_csv(RESULTS_TABLES / "manzala_temporal_metrics.csv", index=False)
            print("Single-scene metrics saved.")
        return

    print("\nBuilding temporal baseline...")
    base_mean, base_std = detection.build_baseline(turb_stack, robust=True)
    _, _, anomaly_summary = detection.detect_anomalies(last_turbidity, base_mean, base_std, last_water_mask)
    print("Anomaly summary:", anomaly_summary)

    # Time-series plot
    fig, ax = plt.subplots(figsize=(8, 4))
    b_mean = float(np.mean(turb_means))
    b_std  = float(np.std(turb_means))
    ax.plot(dates, turb_means, "o-", color="steelblue", label="Mean Turbidity Proxy")
    ax.axhline(b_mean, linestyle="--", color="gray", label=f"Baseline mean={b_mean:.4f}")
    ax.fill_between(dates, b_mean - b_std, b_mean + b_std, color="gray", alpha=0.2, label="±1 std")
    ax.set_title("Lake Manzala — Turbidity Proxy Temporal Baseline (Sentinel-2 L2A)")
    ax.set_ylabel("Red/Green Turbidity Proxy (dimensionless)")
    ax.set_xlabel("Date")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / "manzala_temporal_baseline.png", dpi=150)
    plt.close(fig)
    print("Saved manzala_temporal_baseline.png")

    df = pd.DataFrame({"Date": dates, "Mean_NDWI": ndwi_means, "Mean_Turbidity_Proxy": turb_means})
    df.to_csv(RESULTS_TABLES / "manzala_temporal_metrics.csv", index=False)
    print("Sentinel-2 processing complete.")
    print(df.to_string(index=False))


if __name__ == "__main__":
    run_sentinel()
