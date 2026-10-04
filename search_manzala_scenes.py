"""
Search Sentinel-2 L2A for Lake Manzala across 2024-06-01 to 2025-05-01.
- One tile per date (prefer lowest cloud cover tile when multiple tiles cover the AOI)
- Target 6-8 distinct dates spread across the 12-month window
- Record all metadata
"""
import requests
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

BBOX_MANZALA = [31.00, 30.90, 32.22, 31.35]
DATE_RANGE = "2024-06-01/2025-05-01"
MAX_CLOUD = 15  # slightly relaxed to find enough scenes
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

payload = {
    "collections": ["sentinel-2-l2a"],
    "bbox": BBOX_MANZALA,
    "datetime": DATE_RANGE,
    "query": {"eo:cloud_cover": {"lt": MAX_CLOUD}},
    "limit": 100,
    "sortby": [{"field": "datetime", "direction": "asc"}]
}

print("Querying Planetary Computer STAC...")
r = requests.post(PC_STAC, json=payload)
all_items = r.json().get("features", [])
print(f"Raw results: {len(all_items)} scenes found")

# Group by date, pick best (lowest cloud) tile per date
by_date = defaultdict(list)
for item in all_items:
    date = item["properties"]["datetime"].split("T")[0]
    by_date[date].append(item)

# For each date, pick lowest cloud tile
best_per_date = {}
for date, items in sorted(by_date.items()):
    best = min(items, key=lambda x: x["properties"].get("eo:cloud_cover", 99))
    best_per_date[date] = best

print(f"\nDistinct dates with usable scenes: {len(best_per_date)}")
print("\nAll candidate dates (date, tile, cloud%):")
rows = []
for date, item in best_per_date.items():
    cloud = item["properties"].get("eo:cloud_cover", 99)
    tile = item["id"].split("_")[5]  # e.g. T36RTV
    print(f"  {date}  |  {tile}  |  {cloud:.2f}%  |  {item['id']}")
    rows.append({"date": date, "item_id": item["id"], "tile": tile, "cloud_pct": cloud})

df = pd.DataFrame(rows)
df.to_csv("data/sample_input/manzala_candidate_scenes.csv", index=False)
print(f"\nSaved {len(rows)} candidate scenes to data/sample_input/manzala_candidate_scenes.csv")
