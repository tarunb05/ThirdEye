import json
import sys
from pathlib import Path

# Add backend folder to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.vector_db import add_contract

DATA_FILE = BASE_DIR.parent / "data" / "contracts_example.json"

with open(DATA_FILE) as f:
    data = json.load(f)

for item in data:
    add_contract(item["id"], item["text"])

print("Vector database loaded successfully.")