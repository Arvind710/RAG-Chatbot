"""
LLM Generator using Groq with rate-limit handling.
"""

import logging
from groq import Groq, RateLimitError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from src.utils.config import config
from src.generation.query_guard import QueryGuard, QueryType
from src.generation.prompt_templates import SYSTEM_PROMPT, USER_PROMPT, REFUSAL_MESSAGES
from src.retrieval.retriever import Retriever
from src.utils.formatter import format_response

logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=config.GROQ_API_KEY)

# Initialize Retriever globally to avoid reloading models on every query
retriever = Retriever()


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True
)
def generate_response(system_prompt: str, user_prompt: str) -> str:
    """
    Generate a response from the Groq LLM.
    Implements exponential backoff for RateLimitError to handle strict rate limits.
    """
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        model=config.LLM_MODEL,
        temperature=0.0,
    )
    
    return chat_completion.choices[0].message.content


def answer_query(user_query: str) -> str:
    """
    End-to-end query chain:
    Query Guard -> Retriever -> Prompt Assembly -> Groq LLM -> Formatter
    """
    # 1. Query Guard
    query_type = QueryGuard.check_query(user_query)
    if query_type != QueryType.FACTUAL:
        logger.info(f"Query rejected by guard: {query_type.name}")
        return REFUSAL_MESSAGES[query_type]
        
    # 2. Retriever
    chunks = retriever.retrieve(user_query)
    if not chunks:
        logger.info("No chunks retrieved.")
        return format_response("I don't have this information.", None, None)
        
    # Construct context string and track sources
    context_str = ""
    latest_scrape_date = "0"
    source_url = None
    
    for i, chunk in enumerate(chunks):
        content = chunk['content']
        meta = chunk['metadata']
        context_str += f"--- Chunk {i+1} ---\n{content}\n\n"
        
        # Take the first source url we see (usually they are all for the same scheme if filtered)
        if not source_url:
            source_url = meta.get('source_url')
        
        chunk_date = meta.get('scrape_date', "0")
        if chunk_date > latest_scrape_date:
            latest_scrape_date = chunk_date
            
    # 3. Prompt Assembly
    user_prompt = USER_PROMPT.format(
        retrieved_chunks=context_str.strip(),
        user_query=user_query
    )
    
    # 4. Groq LLM
    try:
        logger.info("Calling Groq LLM...")
        llm_response = generate_response(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return "Sorry, an error occurred while processing your request. Please try again later."
        
    # 5. Formatter
    logger.info("Formatting LLM response...")
    if latest_scrape_date == "0":
        latest_scrape_date = None
        
    formatted_response = format_response(llm_response, source_url, latest_scrape_date)
    return formatted_response
