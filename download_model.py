"""Pre-load ChromaDB's default embedding model so Streamlit doesn't hang."""
print("Initializing ChromaDB to download semantic embedding models (this may take a few minutes on slow connections)...")
import chromadb
from chromadb.utils import embedding_functions

# This triggers the 79MB ONNX download from HuggingFace
ef = embedding_functions.DefaultEmbeddingFunction()
ef(["This is a test document to force download."])
print("Download complete! You can now run the Streamlit app.")
