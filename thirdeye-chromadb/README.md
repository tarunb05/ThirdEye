# thirdeye-chromadb

Local ChromaDB setup for:

- Code4rena reports (`code4rena/Reports/*.pdf`)
- Trail of Bits reports (`trailofbits/Reports/*.pdf`)
- Etherscan verified contracts (`etherscan_verified/*.sol`)

Usage:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_chroma.py

