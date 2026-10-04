import json

NB_PATH = "notebooks/03_aquaspect_colab_executed.ipynb"

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

updated = False
for cell in nb['cells']:
    if cell.get('cell_type') != 'code':
        continue
    src = ''.join(cell.get('source', []))
    if 'PROJECT_ROOT' in src and ('wasfy' in src or 'Local path' in src):
        # Replace entire source with the Colab-ready version
        new_src = (
            "import os, sys, warnings\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import h5py\n"
            "import matplotlib.pyplot as plt\n"
            "import matplotlib.image as mpimg\n"
            "warnings.filterwarnings('ignore')\n"
            "\n"
            "# Mount Google Drive (run this on Colab before the rest):\n"
            "# from google.colab import drive; drive.mount('/content/drive')\n"
            "\n"
            "PROJECT_ROOT = \"/content/drive/MyDrive/AQUASPECT\"  # <- Google Drive path\n"
            "\n"
            "import pathlib\n"
            "PROJECT_ROOT  = pathlib.Path(PROJECT_ROOT)\n"
            "sys.path.insert(0, str(PROJECT_ROOT / \"src\"))\n"
            "\n"
            "from aquaspect import preprocessing, indices, detection\n"
            "\n"
            "DATA_DIR     = PROJECT_ROOT / \"data\" / \"sample_input\"\n"
            "RESULTS_MAPS = PROJECT_ROOT / \"results\" / \"maps\"\n"
            "RESULTS_FIGS = PROJECT_ROOT / \"results\" / \"figures\"\n"
            "RESULTS_TBLS = PROJECT_ROOT / \"results\" / \"tables\"\n"
            "\n"
            "print(\"Project root:\", PROJECT_ROOT)\n"
            "print(\"Maps dir exists:\", RESULTS_MAPS.exists())\n"
            "print(\"Figures dir exists:\", RESULTS_FIGS.exists())\n"
        )
        cell['source'] = [new_src]
        # Clear any stale outputs from local execution
        cell['outputs'] = []
        cell['execution_count'] = None
        updated = True
        print("Updated setup cell.")
        break

if not updated:
    print("ERROR: Setup cell not found!")

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Saved:", NB_PATH)
