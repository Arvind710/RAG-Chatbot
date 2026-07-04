# Mutual Fund FAQ Assistant (RAG Chatbot)

⚠️ **Facts-only. No investment advice.**

## Overview
The Mutual Fund FAQ Assistant is a RAG (Retrieval-Augmented Generation) based chatbot designed to answer factual questions about a specific set of HDFC mutual funds. It processes scheme details, NAVs, expense ratios, holdings, and fund manager profiles from publicly available data, allowing users to query this data reliably. 

The chatbot utilizes an end-to-end ingestion pipeline that scrapes, cleans, and semantically chunks the mutual fund information, storing it in a ChromaDB vector database. User questions are embedded and matched against these facts. A query guard ensures that no advisory queries (e.g., "should I invest in this fund?") or PII (e.g., PAN, Aadhaar) are processed.

## Selected AMC & Schemes

| Scheme | URL |
|---|---|
| HDFC Gold ETF FoF | `https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth` |
| HDFC Large Cap Fund | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |
| HDFC Small Cap Fund | `https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth` |
| HDFC Silver ETF FoF | `https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth` |
| HDFC Mid Cap Fund | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |

## Architecture Summary
The system consists of three main pipelines:
1. **Data Ingestion Pipeline**: Scrapes HTML content from Groww URLs, cleans HTML tags and footer noise, performs section-aware semantic chunking, and embeds chunks using `bge-small-en-v1.5` before storing them in ChromaDB.
2. **Retrieval Pipeline**: Given a query, identifies if a specific scheme is mentioned to filter results, embeds the query, and performs a similarity search in ChromaDB. Post-retrieval deduplication and noise filtering is applied.
3. **Generation Pipeline**: Uses `llama-3.3-70b-versatile` from Groq to format the retrieved chunks into a factual answer of ≤3 sentences. 

A **Query Guard** intercepts and rejects PII and advisory questions before embedding/generation.

## Prerequisites
- Python 3.10+
- Groq API Key
- GitHub repository (for GitHub Actions automated data scheduling)

## Setup Instructions
1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```
2. **Create a virtual environment and activate it**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
4. **Set up `.env` file**
   Create a `.env` file at the root of the project with your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```

## Running Ingestion
To manually trigger the ingestion pipeline and populate the vector store:
```bash
python -m src.ingestion.run_ingestion
```
*Expected Output*: The script will fetch all 5 URLs, clean and chunk the data, and insert the embeddings into `data/vectorstore`.

## Scheduler Configuration
The data is automatically kept fresh via a GitHub Actions workflow.
1. **GitHub Actions Setup**: The workflow `.github/workflows/daily_ingestion.yml` runs daily. 
2. **Repository Secrets**: Navigate to your GitHub repository settings -> Secrets and Variables -> Actions and add `GROQ_API_KEY`.
3. **Workflow Dispatch**: Maintainers can manually trigger ingestion anytime from the "Actions" tab in GitHub by selecting "Daily Data Ingestion" and clicking "Run workflow".
4. **Cron Schedule**: By default, it runs at `30 20 * * *` (02:00 AM IST).

## Launching the App
To start the Streamlit chat interface:
```bash
streamlit run src/app.py
```
*Expected*: The application will launch in your browser at `http://localhost:8501`.

## Running Tests
Run the entire suite of unit and integration tests using pytest:
```bash
pytest tests/ -v
```

## Known Limitations
- Data is refreshed daily via the scheduler, so real-time intra-day NAV updates are not reflected immediately.
- Supported only for the 5 selected HDFC schemes.
- The assistant supports English queries only.
- Designed for single-turn factual questions; no multi-turn or contextual follow-ups are supported.

## Tech Stack

| Component | Technology |
|---|---|
| Application Framework | Streamlit |
| Vector Database | ChromaDB |
| Embeddings | `BAAI/bge-small-en-v1.5` (via `sentence-transformers`) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Scraping | `requests`, `BeautifulSoup`, `playwright` |
| Orchestration & Testing | GitHub Actions, `pytest` |
