import requests

url = 'https://storage.googleapis.com/open-cogs/planet-stac/tanager1-release2-core-imagery/ortho_sr_hdf5/20250926_092059_95_4001_ortho_sr_hdf5.h5'
r = requests.head(url)
print('Status:', r.status_code)
size_gb = int(r.headers.get('content-length', 0)) / (1024**3)
print(f'Size: {size_gb:.2f} GB')
