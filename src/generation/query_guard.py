"""
Query Guard Module.

Provides classification and validation of user queries before they are
sent to the LLM. Blocks queries containing Personal Identifiable Information (PII)
and detects advisory/opinion-based queries to ensure the bot remains facts-only.
"""

import re
import logging
from enum import Enum
from typing import Tuple

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Enum representing the classification of a query."""
    FACTUAL = "FACTUAL"
    ADVISORY = "ADVISORY"
    PII_BLOCKED = "PII_BLOCKED"


# Regex patterns for Personal Identifiable Information (PII)
PII_PATTERNS = {
    # PAN Card: 5 letters, 4 digits, 1 letter
    "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    # Aadhaar Card: 12 digits (often with spaces or hyphens)
    "AADHAAR": r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    # Phone numbers: 10 digits, optionally with +91 or 0 prefix, spaces/hyphens allowed between digits
    "PHONE": r"\b(?:\+91[\s\-]?)?(?:0)?(?:[\s\-]*\d){10}\b",
    # Email addresses
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    # Credit Card numbers: 16 digits, optionally grouped by 4
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
}

# Keywords and phrases indicative of financial advice seeking
ADVISORY_PHRASES = [
    "should i invest",
    "which is better",
    "which one is better",
    "which fund is better",
    "is better",
    "recommend",
    "recommendation",
    "suggest",
    "prediction",
    "good time to buy",
    "good time to invest",
    "is it good to",
    "is this fund good",
    "a good fund",
    "best fund",
    "where should i put my money",
    "how much money",
    "financial advice",
    "investment advice",
    "give me advice",
    "advise me",
    "opinion on",
    "guaranteed returns",
    "forecast",
    "better than",
    "beat inflation",
    "go up",
    "go down",
    "future returns",
    "future performance",
    "buy or sell",
    "how much should i invest",
    "is it safe to invest",
    "portfolio review",
    "multibagger",
]


class QueryGuard:
    """Evaluates queries for PII and advisory intent."""

    @staticmethod
    def detect_pii(query: str) -> Tuple[bool, str]:
        """
        Check if the query contains any PII.
        
        Returns:
            (has_pii, detected_type)
        """
        for pii_type, pattern in PII_PATTERNS.items():
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"PII detected in query: {pii_type}")
                return True, pii_type
        return False, ""

    @staticmethod
    def classify_intent(query: str) -> QueryType:
        """
        Classify whether a query is factual or advisory.
        """
        query_lower = query.lower()
        
        # Handle specific false positive denials
        query_lower = query_lower.replace("not asking for advice", "")
        
        for phrase in ADVISORY_PHRASES:
            # Word boundary check isn't strictly necessary for phrases with spaces,
            # but helps avoid false positives on partial word matches.
            # Using simple substring match for phrases, and word boundary for single words.
            if " " in phrase:
                if phrase in query_lower:
                    logger.info(f"Advisory intent detected via phrase: '{phrase}'")
                    return QueryType.ADVISORY
            else:
                if re.search(rf"\b{phrase}\b", query_lower):
                    logger.info(f"Advisory intent detected via keyword: '{phrase}'")
                    return QueryType.ADVISORY
                    
        return QueryType.FACTUAL

    @staticmethod
    def check_query(query: str) -> QueryType:
        """
        Full check pipeline: PII check first, then intent classification.
        """
        has_pii, _ = QueryGuard.detect_pii(query)
        if has_pii:
            return QueryType.PII_BLOCKED
            
        return QueryGuard.classify_intent(query)
