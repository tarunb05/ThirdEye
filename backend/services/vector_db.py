import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Find project root (since this file is in backend/services)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Path to store the vector database
VECTOR_DB_PATH = BASE_DIR / "data" / "vector_store"

# Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB client (persistent storage)
client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))

# Create or load collection
collection = client.get_or_create_collection(name="contracts")


def add_contract(id: str, text: str):
    """Add a vulnerability example to the vector database"""

    embedding = model.encode(text).tolist()

    collection.add(
        ids=[id],
        documents=[text],
        embeddings=[embedding]
    )


def search_similar(query: str, n_results: int = 3):
    """Search for similar vulnerabilities"""

    embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )

    return results