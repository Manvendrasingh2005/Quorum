"""Vector Store for caching research findings across sessions.

Uses ChromaDB to store Critic-approved research answers. Before doing a web search for a new sub-question,
the Researcher Agent queries Chroma. If a highly similar question already has an approved answer,
we can reuse it—saving time and API costs.
"""
import chromadb
from chromadb.config import Settings
import uuid

# In a real app we'd want this path to be configurable or centralized
CHROMA_DB_DIR = ".chroma_db"

class VectorMemory:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DB_DIR,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Use Gemini API to create embeddings rather than downloading a heavy local model!
            from chromadb.utils import embedding_functions
            from src.config import GEMINI_API_KEY
            gemini_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=GEMINI_API_KEY)
            
            self.collection = self.client.get_or_create_collection(
                name="research_findings",
                embedding_function=gemini_ef,
                metadata={"hnsw:space": "cosine"} # Use cosine similarity for text meaning
            )
            print("[ChromaDB] Initialized using fast Gemini API Embeddings.")
        except Exception as e:
            print(f"[ChromaDB] Warning: Failed to init ChromaDB: {e}. Running without memory.")
            self.collection = None

    def check_memory(self, question: str, max_distance: float = 0.25) -> str | None:
        """
        Check if we have an answer for a highly similar question.
        Returns the answer text if found, else None.
        A smaller distance means high similarity. 0.25 is relatively strict.
        """
        if not self.collection:
            return None

        # Don't fail if the db is empty
        if self.collection.count() == 0:
            return None

        results = self.collection.query(
            query_texts=[question],
            n_results=1
        )
        
        # results["distances"] is list of lists, same for documents
        if results and results["distances"] and results["distances"][0]:
            dist = results["distances"][0][0]
            if dist < max_distance:
                return results["documents"][0][0]
                
        return None

    def store_memory(self, question: str, answer: str, topic: str):
        """Store an approved research finding into the vector store."""
        if not self.collection:
            return

        self.collection.add(
            documents=[answer],
            metadatas=[{"topic": topic}],
            ids=[str(uuid.uuid4())]
        )

# Global singleton
memory = VectorMemory()
