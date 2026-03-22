import os
import glob
import chromadb

DATA_ROOT = "/Users/anvi/Anvita/College/CAPSTONE/thirdeye-data"
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

def load_documents():
    docs, metadatas, ids = [], [], []

    # 1) Code4rena PDFs
    c4_pattern = os.path.join(DATA_ROOT, "code4rena", "Reports", "*.pdf")
    for i, pdf_path in enumerate(glob.glob(c4_pattern)):
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc_id = f"code4rena-{i:03d}"
        docs.append(content.hex())
        metadatas.append({
            "source": "code4rena",
            "filename": os.path.basename(pdf_path),
        })
        ids.append(doc_id)

    # 2) Trail of Bits PDFs
    tob_pattern = os.path.join(DATA_ROOT, "trailofbits", "Reports", "*.pdf")
    for i, pdf_path in enumerate(glob.glob(tob_pattern)):
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc_id = f"tob-{i:03d}"
        docs.append(content.hex())
        metadatas.append({
            "source": "trailofbits",
            "filename": os.path.basename(pdf_path),
        })
        ids.append(doc_id)

    # 3) Etherscan verified .sol files
    eth_pattern = os.path.join(DATA_ROOT, "etherscan_verified", "*.sol")
    for i, sol_path in enumerate(glob.glob(eth_pattern)):
        with open(sol_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        doc_id = f"eth-{i:03d}"
        docs.append(content)
        metadatas.append({
        "source": "etherscan_verified",
        "filename": os.path.basename(sol_path),
        })
        ids.append(doc_id)

    return ids, docs, metadatas


def main():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name="thirdeye_contracts",
        metadata={"hnsw:space": "cosine"},
    )
    ids, docs, metadatas = load_documents()
    if ids:
        collection.add(ids=ids, documents=docs, metadatas=metadatas)
    results = collection.query(query_texts=["medium severity vulnerability"], n_results=3)
    print("Sample query results:", results)

if __name__ == "__main__":
    main()

