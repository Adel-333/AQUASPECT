import os
import requests
from pathlib import Path
import json

def check_file_size(url):
    try:
        r = requests.head(url)
        size_bytes = int(r.headers.get("content-length", 0))
        return size_bytes / (1024**3)
    except Exception as e:
        return str(e)

print("--- AQUASPECT PHASE 2 AUDIT & PRE-CHECK ---")
root = Path("c:/Users/wasfy/Downloads/AQUASPECT")

print("\n1. Directory Structure Check:")
for d in ["data/sample_input", "docs", "notebooks", "results/figures", "results/maps", "results/tables", "src/aquaspect"]:
    path = root / d
    print(f"  {d}: {'PASS' if path.exists() else 'FAIL'}")

print("\n2. File Content Check:")
for f in ["README.md", "requirements.txt", "data/sample_input/scene_manifest.json", "data/sample_input/download_data.py", "notebooks/01_aquaspect_water_quality_poc.ipynb"]:
    path = root / f
    if path.exists():
        size = path.stat().st_size
        print(f"  {f}: PASS ({size} bytes)")
    else:
        print(f"  {f}: FAIL (Not found)")

print("\n3. Tanager HDF5 Size Check:")
tanager_url = "https://storage.googleapis.com/open-cogs/planet-stac/tanager1-release2-core-imagery/ortho_reflectance/20250926_092059_95_4001_ortho_reflectance.h5"
size_gb = check_file_size(tanager_url)
print(f"  Tanager ortho_reflectance.h5 size: {size_gb:.2f} GB")
