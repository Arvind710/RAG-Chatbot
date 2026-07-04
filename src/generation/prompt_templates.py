"""
Prompt templates and predefined responses for the RAG chatbot.
"""

from src.generation.query_guard import QueryType

# ---------------------------------------------------------
# Static Responses (Query Guard Refusals)
# ---------------------------------------------------------

REFUSAL_MESSAGES = {
    QueryType.ADVISORY: (
        "I am an informational assistant and cannot provide financial advice, "
        "fund recommendations, or future performance predictions. For personal "
        "financial advice, please consult a SEBI-registered investment advisor. "
        "You can find educational resources on mutual funds at https://www.amfiindia.com/."
    ),
    QueryType.PII_BLOCKED: (
        "For your privacy and security, please do not share Personal Identifiable "
        "Information (PII) such as PAN, Aadhaar, phone numbers, or email addresses. "
        "Please rephrase your query without sensitive information."
    ),
}

# ---------------------------------------------------------
# LLM System Prompt Templates
# ---------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful, factual mutual fund assistant for HDFC schemes.
Your goal is to answer the user's question based strictly on the provided context.

Rules:
1. Facts-only: ONLY use the information provided in the context below. Do not invent, hallucinate, or assume any information.
2. If the context does not contain the answer, you must exactly say: "I don't have this information."
3. Limit your response to a maximum of 3 sentences.
4. You must provide a citation to the source URL in your response if you found the answer.
"""

USER_PROMPT = """Context Information (Retrieved Chunks):
{retrieved_chunks}

User Question: {user_query}"""
