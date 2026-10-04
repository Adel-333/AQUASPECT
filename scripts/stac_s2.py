import requests
import json

url = 'https://planetarycomputer.microsoft.com/api/stac/v1/search'
payload = {
    'collections': ['sentinel-2-l2a'],
    'bbox': [31.00, 30.90, 32.22, 31.35],
    'datetime': '2025-01-01/2025-05-01',
    'query': {'eo:cloud_cover': {'lt': 10}},
    'limit': 5
}
r = requests.post(url, json=payload)
data = r.json()
print(f"Found {len(data.get('features', []))} S2 scenes for Lake Manzala.")
for f in data.get('features', []):
    print(f"ID: {f['id']}, Date: {f['properties']['datetime']}, Cloud: {f['properties']['eo:cloud_cover']}%")
