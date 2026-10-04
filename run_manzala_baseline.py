"""
Process the full 12-month Sentinel-2 temporal baseline for Lake Manzala.

Selection strategy:
- 8 scenes from DISTINCT DATES
- Spread across the full 2024-06-01 to 2025-05-01 window
- One scene per ~6-week interval to capture seasonal variability
- Prefer lowest cloud cover when multiple options exist per interval
"""
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import json
from datetime import datetime

PROJECT_ROOT = Path("c:/Users/wasfy/Downloads/AQUASPECT")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aquaspect import indices, detection, visualization

DATA_DIR   = PROJECT_ROOT / "data" / "sample_input"
RESULTS_FIGURES = PROJECT_ROOT / "results" / "figures"
RESULTS_MAPS    = PROJECT_ROOT / "results" / "maps"
RESULTS_TABLES  = PROJECT_ROOT / "results" / "tables"

BBOX_MANZALA = [31.00, 30.90, 32.22, 31.35]

# -----------------------------------------------------------------------
# 8 scenes hand-picked for ~6-week spacing across 12 months
# One tile per date, lowest cloud cover
# -----------------------------------------------------------------------
SELECTED_SCENES = [
    # (date,  item_id,  tile,  cloud_pct)
    ("2024-06-06", "S2A_MSIL2A_20240606T082611_R021_T36RUV_20240606T142017", "T36RUV", 0.00),
    ("2024-07-21", "S2B_MSIL2A_20240721T082609_R021_T36RTV_20240721T115912", "T36RTV", 0.00),
    ("2024-08-20", "S2B_MSIL2A_20240820T082559_R021_T36RTV_20240820T130351", "T36RTV", 0.00),
    ("2024-09-27", "S2A_MSIL2A_20240927T083731_R064_T36RUV_20240927T130851", "T36RUV", 0.00),
    ("2024-10-04", "S2A_MSIL2A_20241004T082811_R021_T36RVV_20241004T115852", "T36RVV", 5.94),
    # For Nov-Dec-Jan: search returned no results ≤15% in the 100-item page;
    # will attempt a separate query
    ("2025-04-27", "S2A_MSIL2A_20250427T084501_R064_T36RTV_20250427T140513", "T36RTV", 3.97),
]

import tifffile
import imagecodecs  # noqa – ensures tifffile can decode 15-bit packints

PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"


def sign_href(href, retries=5):
    """Sign a Planetary Computer href with retry + exponential backoff."""
    import time
    for attempt in range(retries):
        try:
            r = requests.get(
                f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={href}",
                timeout=30,
            )
            if r.status_code == 200 and r.text.strip():
                return r.json()["href"]
            return href
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"    sign_href attempt {attempt+1} failed ({e}). Retry in {wait}s...")
            time.sleep(wait)
    print("    sign_href exhausted retries, using unsigned URL.")
    return href


def fetch_item(item_id):
    """Re-fetch a STAC item to get fresh signed asset URLs."""
    # Search by ID
    payload = {
        "collections": ["sentinel-2-l2a"],
        "ids": [item_id],
        "limit": 1,
    }
    r = requests.post(PC_STAC, json=payload)
    feats = r.json().get("features", [])
    if not feats:
        raise ValueError(f"Item not found: {item_id}")
    return feats[0]


def dl_band(item_id, href, band_name, cache_dir, retries=4):
    """Download a single band with retry + backoff. Skip if already cached."""
    import time
    dest = cache_dir / f"{item_id}_{band_name}.tif"
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    print(f"    DL {band_name}...")
    for attempt in range(retries):
        try:
            signed = sign_href(href)
            with requests.get(signed, stream=True, timeout=180) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                        f.write(chunk)
            return dest
        except Exception as e:
            wait = 8 * (2 ** attempt)
            print(f"    dl_band {band_name} attempt {attempt+1} failed ({e}). Retry in {wait}s...")
            time.sleep(wait)
            if dest.exists():
                dest.unlink()
    raise RuntimeError(f"Failed to download {band_name} for {item_id} after {retries} attempts.")


def load_band(path, stride):
    arr = tifffile.imread(str(path))
    return arr[::stride, ::stride].astype(np.float32)


def process_scene(item_id, date_str, tile, cloud_pct):
    print(f"\n  Processing {date_str} | {tile} | {cloud_pct:.2f}% cloud")
    item = fetch_item(item_id)

    b3_path  = dl_band(item_id, item["assets"]["B03"]["href"],  "B03",  DATA_DIR)
    b4_path  = dl_band(item_id, item["assets"]["B04"]["href"],  "B04",  DATA_DIR)
    b8a_path = dl_band(item_id, item["assets"]["B8A"]["href"],  "B8A",  DATA_DIR)
    scl_path = dl_band(item_id, item["assets"]["SCL"]["href"],  "SCL",  DATA_DIR)

    s10, s20 = 10, 5     # stride → 100 m effective
    b3  = load_band(b3_path,  s10) / 10000.0
    b4  = load_band(b4_path,  s10) / 10000.0
    b8a = load_band(b8a_path, s20) / 10000.0
    scl = load_band(scl_path, s20)

    ny = min(b3.shape[0], b8a.shape[0], scl.shape[0])
    nx = min(b3.shape[1], b8a.shape[1], scl.shape[1])
    b3, b4, b8a, scl = b3[:ny,:nx], b4[:ny,:nx], b8a[:ny,:nx], scl[:ny,:nx]

    valid = np.isin(scl.astype(int), [4, 5, 6, 7])
    b3[~valid] = np.nan
    b4[~valid] = np.nan
    b8a[~valid] = np.nan

    ndwi_arr = indices.ndwi(b3, b8a)
    ndci_arr = indices.ndci(b8a, b4)   # approximate: B8A≈RE, B4=Red
    turb_arr = indices.turbidity_proxy(b4, b3)

    wm_raw = indices.water_mask(ndwi_arr, threshold=0.1)
    wm, wm_stats = detection.apply_water_mask(wm_raw & valid, min_pixels=10, pixel_area_m2=10000)

    n_water = int(np.sum(wm))
    if n_water == 0:
        print(f"    WARNING: No water pixels found for {date_str}. Skipping.")
        return None

    s_ndwi = detection.spatial_stats(ndwi_arr, wm, name="NDWI")
    s_turb = detection.spatial_stats(turb_arr, wm, name="Turbidity")
    s_ndci = detection.spatial_stats(ndci_arr, wm, name="NDCI")

    t_obs = turb_arr.copy()
    t_obs[~wm] = np.nan

    print(f"    Water px: {n_water:,} | NDWI: {s_ndwi['NDWI_mean']:.4f} | Turb: {s_turb['Turbidity_mean']:.4f} | NDCI: {s_ndci['NDCI_mean']:.4f}")

    return {
        "date": date_str,
        "item_id": item_id,
        "tile": tile,
        "cloud_pct": cloud_pct,
        "water_pixels": n_water,
        "water_area_km2": round(n_water * 10000 / 1e6, 2),
        "mean_ndwi": s_ndwi["NDWI_mean"],
        "mean_turbidity": s_turb["Turbidity_mean"],
        "std_turbidity":  s_turb["Turbidity_std"],
        "mean_ndci": s_ndci["NDCI_mean"],
        "turb_obs": t_obs,
        "water_mask": wm,
    }


# -----------------------------------------------------------------------
# Also search for winter scenes (Nov 2024 – Jan 2025) that may be missing
# -----------------------------------------------------------------------
def search_winter():
    extra_scenes = []
    for window in [("2024-11-01", "2025-01-31"), ("2025-02-01", "2025-03-31")]:
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": BBOX_MANZALA,
            "datetime": f"{window[0]}/{window[1]}",
            "query": {"eo:cloud_cover": {"lt": 30}},
            "limit": 20,
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        }
        r = requests.post(PC_STAC, json=payload)
        feats = r.json().get("features", [])
        seen_dates = set()
        for item in feats:
            date = item["properties"]["datetime"].split("T")[0]
            if date not in seen_dates:
                seen_dates.add(date)
                tile = item["id"].split("_")[5]
                cloud = item["properties"].get("eo:cloud_cover", 99)
                extra_scenes.append((date, item["id"], tile, cloud))
                if len(extra_scenes) >= 2:
                    break
        if len(extra_scenes) >= 2:
            break
    return extra_scenes[:2]


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main():
    print("=== MANZALA TEMPORAL BASELINE — 12-MONTH EXPANSION ===\n")

    # Add winter scenes
    print("Searching for winter/spring scenes...")
    winter = search_winter()
    for w in winter:
        print(f"  Found: {w[0]} | {w[2]} | {w[3]:.2f}%")

    all_scenes = list(SELECTED_SCENES) + winter
    # Sort by date and deduplicate
    all_scenes = sorted(set(all_scenes), key=lambda x: x[0])
    print(f"\nTotal scenes to process: {len(all_scenes)}")

    results = []
    turb_stack = []
    for date_str, item_id, tile, cloud_pct in all_scenes:
        r = process_scene(item_id, date_str, tile, cloud_pct)
        if r is not None:
            results.append(r)
            turb_stack.append(r["turb_obs"])

    if len(results) < 2:
        print("FATAL: Fewer than 2 usable scenes. Cannot build baseline.")
        return

    print(f"\n=== BASELINE: {len(results)} usable distinct dates ===")

    # -----------------------------------------------------------------------
    # Temporal baseline + anomaly on LAST observation
    # -----------------------------------------------------------------------
    base_mean, base_std = detection.build_baseline(turb_stack[:-1], robust=True)
    last_obs   = results[-1]["turb_obs"]
    last_wm    = results[-1]["water_mask"]
    _, anomaly_class, anomaly_summary = detection.detect_anomalies(
        last_obs, base_mean, base_std, last_wm
    )
    print(f"Anomaly detection on {results[-1]['date']}: {anomaly_summary}")

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    df = pd.DataFrame([
        {
            "date": r["date"],
            "item_id": r["item_id"],
            "tile": r["tile"],
            "cloud_pct": r["cloud_pct"],
            "water_pixels": r["water_pixels"],
            "water_area_km2": r["water_area_km2"],
            "mean_ndwi": round(r["mean_ndwi"], 5),
            "mean_turbidity": round(r["mean_turbidity"], 5),
            "std_turbidity": round(r["std_turbidity"], 5),
            "mean_ndci": round(r["mean_ndci"], 5),
        }
        for r in results
    ])
    df.to_csv(RESULTS_TABLES / "manzala_temporal_metrics.csv", index=False)
    print("\nMetrics table:")
    print(df[["date", "tile", "cloud_pct", "water_pixels", "mean_ndwi", "mean_turbidity", "mean_ndci"]].to_string(index=False))

    # -----------------------------------------------------------------------
    # Time-series plot (Redesigned)
    # -----------------------------------------------------------------------
    dates_dt = [datetime.strptime(r["date"], "%Y-%m-%d") for r in results]
    turb_vals = [r["mean_turbidity"] for r in results]
    ndwi_vals = [r["mean_ndwi"] for r in results]

    b_med = float(np.median(turb_vals))
    b_std = float(np.std(turb_vals))

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True)

    # Top: turbidity proxy
    ax1 = axes[0]
    ax1.plot(dates_dt, turb_vals, "o-", color="#c0392b", linewidth=2, markersize=8, label="Mean Turbidity Proxy")
    ax1.axhline(b_med, linestyle="--", color="#7f8c8d", alpha=0.9, label=f"12-Month Median ({b_med:.4f})")
    ax1.fill_between(dates_dt, b_med - b_std, b_med + b_std, color="#bdc3c7", alpha=0.2, label="±1 Standard Deviation")
    
    if anomaly_summary.get("anomaly_elevated_px", 0) > 0:
        ax1.axvline(dates_dt[-1], color="#e74c3c", linestyle=":", linewidth=2, alpha=0.8, label="Observation (Anomaly Screening)")
        
    ax1.set_ylabel("Turbidity Proxy\n(Red/Green Ratio)", fontsize=11, fontweight="medium")
    ax1.set_title("Lake Manzala — 12-Month Temporal Baseline (Sentinel-2 L2A)", fontsize=14, fontweight="bold", pad=15)
    ax1.legend(fontsize=10, loc="upper right", frameon=True, shadow=False)
    ax1.tick_params(axis="y", labelsize=10)

    # Bottom: NDWI 
    ax2 = axes[1]
    ax2.plot(dates_dt, ndwi_vals, "s-", color="#2980b9", linewidth=2, markersize=8, label="Mean NDWI (Water Extent Proxy)")
    ndwi_med = float(np.median(ndwi_vals))
    ax2.axhline(ndwi_med, linestyle="--", color="#7f8c8d", alpha=0.9, label=f"Median NDWI ({ndwi_med:.4f})")
    ax2.set_ylabel("Mean NDWI", fontsize=11, fontweight="medium")
    ax2.set_xlabel("Acquisition Date", fontsize=11, fontweight="medium")
    ax2.legend(fontsize=10, loc="lower right", frameon=True)
    ax2.tick_params(axis="both", labelsize=10)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=30)
    
    # Removed overlapping cloud% text annotations; the table handles this cleanly.

    fig.tight_layout()
    save_path = RESULTS_FIGURES / "manzala_temporal_baseline.png"
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved {save_path}")

    # -----------------------------------------------------------------------
    # Anomaly summary save
    # -----------------------------------------------------------------------
    anom_df = pd.DataFrame([{
        "reference_date": results[-1]["date"],
        **anomaly_summary
    }])
    anom_df.to_csv(RESULTS_TABLES / "manzala_anomaly_summary.csv", index=False)

    # -----------------------------------------------------------------------
    # Execution log
    # -----------------------------------------------------------------------
    log_dir = PROJECT_ROOT / "outputs" / "phase2"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "execution_log.txt"
    with open(log_path, "w") as f:
        f.write("AQUASPECT — Manzala Temporal Baseline Execution Log\n")
        f.write("=" * 55 + "\n")
        f.write(f"Search window: 2024-06-01 to 2025-05-01\n")
        f.write(f"Scenes processed: {len(results)}\n\n")
        for r in results:
            f.write(f"{r['date']} | {r['tile']} | cloud={r['cloud_pct']:.2f}% | "
                    f"water_px={r['water_pixels']:,} | mean_turb={r['mean_turbidity']:.5f}\n")
        f.write(f"\nBaseline median turbidity: {b_med:.5f}\n")
        f.write(f"Baseline std turbidity: {b_std:.5f}\n")
        f.write(f"\nAnomaly (last obs = {results[-1]['date']}):\n")
        for k, v in anomaly_summary.items():
            f.write(f"  {k}: {v}\n")
    print(f"Saved execution log: {log_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
