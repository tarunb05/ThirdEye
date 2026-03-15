import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.vector_db import search_similar

query = "smart contract with reentrancy vulnerability"

results = search_similar(query)

print(results)