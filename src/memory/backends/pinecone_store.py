import pinecone
from sentence_transformers import SentenceTransformer
from ...interfaces import BaseVectorStore, MemoryConfig
from typing import List, Dict, Any

class PineconeStore(BaseVectorStore):
    def __init__(self, config: MemoryConfig):
        pinecone.init(api_key=config.pinecone_key, environment=config.pinecone_env)
        self.index = pinecone.Index(config.pinecone_index)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_and_store(self, text: str, metadata: Dict[str, Any]) -> str:
        vec = self.embedder.encode(text).tolist()
        vec_id = f"vec_{hash(text)}"  # Unique ID
        self.index.upsert(vectors=[{"id": vec_id, "values": vec, "metadata": metadata}])
        return vec_id

    def query_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        q_vec = self.embedder.encode(query).tolist()
        results = self.index.query(vector=q_vec, top_k=top_k, include_metadata=True)
        return [match['metadata'] for match in results['matches']]