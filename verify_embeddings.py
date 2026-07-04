import chromadb
from src.utils.config import config

def verify_embeddings():
    print(f"Connecting to ChromaDB at: {config.VECTORSTORE_DIR}")
    client = chromadb.PersistentClient(path=config.VECTORSTORE_DIR)
    
    collection = client.get_collection("mutual_funds")
    
    count = collection.count()
    print(f"\nTotal chunks in ChromaDB: {count}")
    
    if count == 0:
        print("No embeddings found.")
        return
        
    print("\nFetching all items from the collection...\n")
    # Fetch all items (including embeddings, documents, and metadatas)
    results = collection.get(include=['embeddings', 'documents', 'metadatas'])
    
    for i in range(count):
        print("-" * 60)
        print(f"Chunk ID : {results['ids'][i]}")
        print(f"Metadata : {results['metadatas'][i]}")
        
        # Truncate content for display
        doc = results['documents'][i]
        display_doc = doc if len(doc) < 150 else doc[:150] + "..."
        print(f"Content  : {display_doc}")
        
        # Display embedding info
        embedding = results['embeddings'][i]
        print(f"Embedding: Length = {len(embedding)} | First 5 dims = {embedding[:5]}")
        
    print("-" * 60)
    print(f"\nVerification complete. Displayed {count} chunks.")

if __name__ == "__main__":
    verify_embeddings()
