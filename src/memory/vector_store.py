"""Vector Store for caching research findings across sessions.

Uses ChromaDB to store Critic-approved research answers. Before doing a web search for a new sub-question,
the Researcher Agent queries Chroma. If a highly similar question already has an approved answer,
we can reuse it—saving time and API costs.
"""
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.config import Settings
import time
import uuid

# In a real app we'd want this path to be configurable or centralized
CHROMA_DB_DIR = ".chroma_db"

class GeminiGenAiEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return self.embed_documents(input)

    def embed_documents(self, input: Documents) -> Embeddings:
        from src.agents.base import _client
        embeddings = []
        for text in input:
            try:
                res = _client.models.embed_content(model="gemini-embedding-001", contents=text)
                embeddings.append(res.embeddings[0].values)
            except Exception as e:
                print(f"[GeminiEmbedding] Failed to embed text: {e}")
                # Fallback zero vector if model call fails
                embeddings.append([0.0] * 3072)
        return embeddings

    def embed_query(self, input: Documents) -> Embeddings:
        return self.embed_documents(input)

class VectorMemory:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DB_DIR,
                settings=Settings(anonymized_telemetry=False)
            )
            
            gemini_ef = GeminiGenAiEmbeddingFunction()
            
            try:
                self.collection = self.client.get_or_create_collection(
                    name="research_findings_v2",
                    embedding_function=gemini_ef,
                    metadata={"hnsw:space": "cosine"} # Use cosine similarity for text meaning
                )
            except Exception:
                try:
                    self.client.delete_collection("research_findings_v2")
                except Exception:
                    pass
                self.collection = self.client.get_or_create_collection(
                    name="research_findings_v2",
                    embedding_function=gemini_ef,
                    metadata={"hnsw:space": "cosine"}
                )
            print("[ChromaDB] Initialized using native Gemini API Embeddings.")
        except Exception as e:
            print(f"[ChromaDB] Warning: Failed to init ChromaDB: {e}. Running without memory.")
            self.collection = None

    def check_memory(self, question: str, max_distance: float = 0.20, max_age_days: int = 30) -> str | None:
        """
        Check if we have an answer for a highly similar question.
        Returns the answer text if found and not expired, else None.
        Cosine distance < 0.20 represents strong semantic equivalence.
        """
        if not self.collection:
            return None

        # Don't fail if the db is empty
        if self.collection.count() == 0:
            return None

        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=1
            )
            
            # results["distances"] is list of lists, same for documents
            if results and results["distances"] and results["distances"][0]:
                dist = results["distances"][0][0]
                if dist < max_distance:
                    meta = results["metadatas"][0][0] if results.get("metadatas") else None
                    if meta:
                        # TTL expiration check
                        created_at = meta.get("created_at")
                        if created_at and (time.time() - created_at > max_age_days * 86400):
                            return None # Cache entry expired
                        if "answer" in meta:
                            return meta["answer"]
                    # Fallback for documents stored as answers in legacy format
                    return results["documents"][0][0]
        except Exception as e:
            print(f"[VectorMemory] Cache query failed: {e}")
            return None
                
        return None

    def store_memory(self, question: str, answer: str, topic: str):
        """Store an approved research finding into the vector store, indexed by question."""
        if not self.collection:
            return

        try:
            self.collection.add(
                documents=[question],
                metadatas=[{
                    "topic": topic,
                    "question": question,
                    "answer": answer,
                    "created_at": time.time(),
                }],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            print(f"[VectorMemory] Failed to store memory: {e}")

# Global singleton
memory = VectorMemory()
