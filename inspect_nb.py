import json

with open('notebooks/03_aquaspect_final_poc_executed.ipynb', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))[:80].replace('\n', ' ')
    outputs = cell.get('outputs', [])
    img_count = sum(1 for o in outputs if 'image/png' in o.get('data', {}))
    has_error = any(o.get('output_type') == 'error' for o in outputs)
    print(f"Cell {i:02d} | {cell['cell_type'][:4]} | imgs={img_count} | err={has_error} | {src}")
