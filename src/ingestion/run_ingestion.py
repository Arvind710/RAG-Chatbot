"""Script to run the full data ingestion pipeline."""
from src.ingestion.scraper import run_scraper
from src.ingestion.cleaner import run_cleaner
from src.ingestion.chunker import run_chunker
from src.embeddings.embedder import Embedder

def main():
    """Execute the full ingestion pipeline: scrape, clean, chunk, embed, and store."""
    print("==================================================")
    print("    Starting Data Ingestion Pipeline...          ")
    print("==================================================")
    
    print("\n--- Step 1: Web Scraping ---")
    run_scraper()
    
    print("\n--- Step 2: Text Cleaning ---")
    run_cleaner()
    
    print("\n--- Step 3: Semantic Chunking ---")
    run_chunker()
    
    print("\n--- Step 4: Embedding and Storing in ChromaDB ---")
    embedder = Embedder()
    embedder.process_all_chunks()
    
    print("\n==================================================")
    print("    Ingestion Pipeline Completed Successfully!   ")
    print("==================================================")

if __name__ == "__main__":
    main()
