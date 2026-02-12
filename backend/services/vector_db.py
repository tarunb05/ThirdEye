import chromadb
from pathlib import Path

def get_client():
    '''Get or create ChromaDB persistent client'''
    db_path = Path(__file__).parent.parent / 'data' / 'vector_store'
    db_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(db_path))

def get_contract_collection():
    '''Get or create contracts collection'''
    client = get_client()
    return client.get_or_create_collection('contracts')

def find_similar_exploits(vulnerability_type: str, n_results: int = 3) -> list:
    '''Query vector DB for similar exploits'''
    try:
        collection = get_contract_collection()
        query = f'contracts with {vulnerability_type} vulnerability'
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    except Exception as e:
        return []
