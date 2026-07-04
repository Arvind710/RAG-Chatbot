"""
Response formatter for the RAG chatbot.
"""

import datetime
from nltk.tokenize import sent_tokenize

def format_response(llm_response: str, source_url: str = None, scrape_date: str = None) -> str:
    """
    Format the LLM response to meet the following requirements:
    - Maximum 3 sentences.
    - Append source citation URL.
    - Append footer with the last updated date.
    - Handle "I don't have this information." gracefully.
    """
    # 1. Handle edge case for lack of information
    if "i don't have this information" in llm_response.lower():
        return "I don't have this information."

    # 2. Enforce 3-sentence limit
    # We use sent_tokenize to safely split sentences.
    # Avoid truncating if the response contains markdown lists or tables as it could break them.
    if '|' not in llm_response and not ('\n-' in llm_response or '\n*' in llm_response):
        sentences = sent_tokenize(llm_response)
        if len(sentences) > 3:
            llm_response = " ".join(sentences[:3])
            
    # 3. Append source citation URL and footer
    formatted_response = llm_response.strip()
    
    if source_url:
        formatted_response += f"\n\nSource: {source_url}"
        
    if scrape_date:
        try:
            # Check if it's a unix timestamp (could be string or int/float)
            timestamp = float(scrape_date)
            # Convert to YYYY-MM-DD
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except ValueError:
            # It's not a numeric timestamp, treat as string and grab first 10 chars
            date_str = str(scrape_date)[:10]
        formatted_response += f"\nLast updated from sources: {date_str}"
    else:
        today = datetime.date.today().isoformat()
        formatted_response += f"\nLast updated from sources: {today}"
        
    return formatted_response
