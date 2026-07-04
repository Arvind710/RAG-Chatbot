"""Module for generating embeddings using sentence-transformers."""
import os
import json
import uuid
from sentence_transformers import SentenceTransformer
import chromadb
from src.utils.config import config

class Embedder:
    """Class to handle text embeddings."""
    def __init__(self):
        """Initialize the Embedder with the specified model."""
        print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        
        print(f"Initializing ChromaDB client at: {config.VECTORSTORE_DIR}")
        self.chroma_client = chromadb.PersistentClient(path=config.VECTORSTORE_DIR)
        
        # BGE models use cosine similarity.
        self.collection = self.chroma_client.get_or_create_collection(
            name="mutual_funds",
            metadata={"hnsw:space": "cosine"}
        )
    
    def process_all_chunks(self):
        """
        Loads all chunks from processed JSON files, generates embeddings, 
        and stores them in ChromaDB.
        """
        all_contents = []
        all_metadata = []
        all_ids = []
        
        if not os.path.exists(config.PROCESSED_DATA_DIR):
            print(f"Processed data directory not found: {config.PROCESSED_DATA_DIR}")
            return
            
        for filename in os.listdir(config.PROCESSED_DATA_DIR):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(config.PROCESSED_DATA_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    chunks = json.load(f)
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON file: {filename}")
                    continue
                
            for chunk in chunks:
                all_contents.append(chunk['content'])
                all_metadata.append(chunk['metadata'])
                # Using uuid for unique chunk ID
                all_ids.append(str(uuid.uuid4()))
                
        if not all_contents:
            print("No chunks found to embed.")
            return

        print(f"Embedding {len(all_contents)} chunks in a single pass...")
        
        # Batch embed all chunks. Fits in memory.
        embeddings = self.model.encode(all_contents, show_progress_bar=True)
        
        print(f"Storing {len(all_contents)} embeddings + metadata in ChromaDB...")
        self.collection.add(
            ids=all_ids,
            embeddings=embeddings.tolist(),
            documents=all_contents,
            metadatas=all_metadata
        )
        print("Embeddings stored successfully!")

    def embed_query(self, query):
        """
        Embed a query using the recommended BGE instruction prefix.
        """
        query_instruction = "Represent this sentence for searching relevant passages: "
        query_with_instruction = query_instruction + query
        return self.model.encode(query_with_instruction).tolist()

if __name__ == "__main__":
    embedder = Embedder()
    embedder.process_all_chunks()
