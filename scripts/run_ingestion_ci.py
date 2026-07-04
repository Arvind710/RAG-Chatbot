"""CI script to run the data ingestion pipeline and log results."""
import sys
import os
import time
import json
import traceback
from datetime import datetime
import requests

# Ensure src is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.run_ingestion import main as run_ingestion_main
import chromadb

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "ingestion_log.json")
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")

def perform_health_check():
    """Perform a health check on the target domain."""
    print("Performing health check on groww.in...")
    try:
        response = requests.head("https://groww.in", timeout=10)
        response.raise_for_status()
        print("Health check passed.")
    except Exception as e:
        print(f"Health check failed: {e}")
        raise

def get_chunk_count():
    """Get the number of chunks currently stored in ChromaDB."""
    if not os.path.exists(VECTORSTORE_DIR):
        return 0
    try:
        client = chromadb.PersistentClient(VECTORSTORE_DIR)
        collection = client.get_collection("mutual_funds")
        return collection.count()
    except Exception:
        return 0

def write_log(status, duration_seconds, chunks_count, error_message=None):
    """Write an entry to the ingestion log."""
    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "duration_seconds": round(duration_seconds, 2),
        "chunks_count": chunks_count,
        "error_message": error_message
    }
    
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)
    print(f"Log written to {LOG_FILE}: {log_data}")

def main():
    """Main execution function for the CI ingestion script."""
    start_time = time.time()
    try:
        perform_health_check()
        
        print("Starting ingestion pipeline...")
        run_ingestion_main()
        
        chunks_count = get_chunk_count()
        print(f"Post-ingestion chunk count: {chunks_count}")
        
        duration = time.time() - start_time
        write_log("success", duration, chunks_count)
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        print(f"Ingestion failed: {error_msg}")
        traceback.print_exc()
        
        duration = time.time() - start_time
        chunks_count = get_chunk_count()
        write_log("failure", duration, chunks_count, error_message=error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
