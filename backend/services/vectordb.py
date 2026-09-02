"""
ChromaDB vector store for contract analysis history.
Stores past analyses so Raven can learn from previous scans.
Falls back gracefully if ChromaDB isn't installed.
"""
import json
import os

ENABLE_VECTORDB = os.getenv("ENABLE_VECTORDB", "true").lower() != "false"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if not ENABLE_VECTORDB:
        return None
    if _collection is not None:
        return _collection
    try:
        import chromadb
        _client = chromadb.PersistentClient(path="./data/vectordb")
        _collection = _client.get_or_create_collection(
            name="contract_analyses",
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except ImportError:
        print("[Raven] ChromaDB not installed — running without vector memory (pip install chromadb)")
        return None
    except Exception as e:
        print(f"[Raven] ChromaDB error: {e}")
        return None


def store_analysis(code_hash: str, code: str, result: dict):
    """Store an analysis in the vector DB for future similarity search."""
    col = _get_collection()
    if col is None:
        return

    vulns = result.get("vulnerabilities", [])
    vuln_types = [v.get("type", "") for v in vulns]
    verdict = result.get("final_verdict", "UNKNOWN")

    # Create a rich text document for embedding
    doc = f"""Contract: {result.get('contract_name', 'Unknown')}
Verdict: {verdict}
Vulnerabilities: {', '.join(vuln_types) if vuln_types else 'None'}
Summary: {result.get('summary', '')[:200]}
Code snippet: {code[:300]}"""

    metadata = {
        "verdict": verdict,
        "vuln_count": len(vulns),
        "vulns_summary": ", ".join(vuln_types[:5]) if vuln_types else "clean",
        "contract_name": result.get("contract_name", ""),
    }

    try:
        col.upsert(
            ids=[code_hash],
            documents=[doc],
            metadatas=[metadata],
        )
    except Exception as e:
        print(f"[Raven] Vector store error: {e}")


def find_similar(code_or_hash: str, n: int = 3) -> list[dict]:
    """Find similar past analyses."""
    col = _get_collection()
    if col is None:
        return []

    try:
        # If it looks like code, search by content
        query = code_or_hash if len(code_or_hash) > 20 else f"contract with hash {code_or_hash}"
        results = col.query(query_texts=[query], n_results=n)

        similar = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                similar.append(meta)
        return similar
    except Exception as e:
        print(f"[Raven] Similarity search error: {e}")
        return []
