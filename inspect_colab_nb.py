import json

with open('notebooks/03_aquaspect_colab_executed.ipynb', encoding='utf-8') as f:
    nb = json.load(f)

total_imgs = 0
for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))[:70].replace('\n', ' ')
    outputs = cell.get('outputs', [])
    img_count = sum(1 for o in outputs if 'image/png' in o.get('data', {}))
    has_error = any(o.get('output_type') == 'error' for o in outputs)
    total_imgs += img_count
    ct = cell['cell_type'][:4]
    print(f"Cell {i:02d} | {ct} | imgs={img_count} | err={has_error} | {src}")

print(f"\nTotal embedded images: {total_imgs}")
