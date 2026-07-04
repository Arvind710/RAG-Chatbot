"""Configuration module for the Mutual Fund FAQ Assistant."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class Config:
    # API Keys
    """Class to hold configuration variables loaded from the environment."""
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in the environment.")

    
    # Models
    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
    LLM_MODEL = "llama-3.1-8b-instant"  # Using 3.1 8B instant model because 70B hit rate limits
    
    # Chunker & Retrieval Settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    TOP_K = 25
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
    PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
    VECTORSTORE_DIR = os.path.join(DATA_DIR, "vectorstore")

config = Config()
