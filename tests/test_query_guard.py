"""
Tests for the Query Guard module (Phase 3).
Verifies that factual queries are allowed, while PII and advisory queries are blocked.
"""

import pytest
from src.generation.query_guard import QueryGuard, QueryType


class TestQueryGuard:
    
    def test_factual_queries_pass(self):
        factual_queries = [
            "What is the expense ratio of HDFC Small Cap Fund?",
            "Who is the fund manager for HDFC Mid Cap?",
            "What is the minimum SIP amount for Gold ETF?",
            "List the top 10 holdings of HDFC Large Cap.",
            "What is the NAV of HDFC Silver ETF?",
            "What are the 3-year returns of HDFC Mid Cap?",
            "What is the benchmark index for HDFC Small Cap Fund?",
            "Does HDFC Mid Cap invest in HDFC Bank?",
            "What is the total AUM of HDFC Large Cap Fund?",
            "When was the HDFC Gold ETF launched?"
        ]
        
        for q in factual_queries:
            assert QueryGuard.check_query(q) == QueryType.FACTUAL, f"Failed on factual query: {q}"

    def test_advisory_queries_blocked(self):
        advisory_queries = [
            "Should I invest in HDFC Small Cap or Mid Cap?",
            "Which fund is better for long term growth?",
            "Do you recommend HDFC Large Cap Fund?",
            "What is your prediction for HDFC Gold ETF returns next year?",
            "Can you suggest a good mutual fund for my retirement?",
            "Is it a good time to buy HDFC Silver ETF?",
            "Is HDFC Mid Cap a good fund?",
            "What is the best fund to invest 1000 rupees in?",
            "Where should I put my money right now?",
            "I need some investment advice.",
            "Will HDFC Small Cap go up in 2024?",
            "Will the market go down tomorrow?",
            "What are the future returns of this fund?",
            "Should I buy or sell my HDFC Large Cap units?",
            "How much should I invest in HDFC Gold ETF?"
        ]
        
        for q in advisory_queries:
            assert QueryGuard.check_query(q) == QueryType.ADVISORY, f"Failed on advisory query: {q}"

    def test_pii_pan_detection(self):
        queries = [
            "My PAN is ABCDE1234F. What is my portfolio?",
            "Can you link my pan card (abcde1234f) to this fund?",
            "Here is my PAN: ZZZZZ9999Z"
        ]
        for q in queries:
            assert QueryGuard.check_query(q) == QueryType.PII_BLOCKED, f"Failed on PAN PII: {q}"

    def test_pii_aadhaar_detection(self):
        queries = [
            "My Aadhaar is 1234 5678 9012.",
            "Here is my aadhaar number: 123456789012",
            "Aadhaar: 1234-5678-9012"
        ]
        for q in queries:
            assert QueryGuard.check_query(q) == QueryType.PII_BLOCKED, f"Failed on Aadhaar PII: {q}"

    def test_pii_phone_detection(self):
        queries = [
            "Call me at 9876543210.",
            "My mobile is +91 9876543210",
            "Contact: 09876543210"
        ]
        for q in queries:
            assert QueryGuard.check_query(q) == QueryType.PII_BLOCKED, f"Failed on Phone PII: {q}"

    def test_pii_email_detection(self):
        queries = [
            "Email me the details at user@example.com",
            "My id is test.user123@gmail.co.in.",
            "Send it to admin@company.org please."
        ]
        for q in queries:
            assert QueryGuard.check_query(q) == QueryType.PII_BLOCKED, f"Failed on Email PII: {q}"

    def test_pii_credit_card_detection(self):
        queries = [
            "My card is 4111-1111-1111-1111",
            "Credit card number: 1234 5678 1234 5678",
            "Here is the card: 1234567812345678"
        ]
        for q in queries:
            assert QueryGuard.check_query(q) == QueryType.PII_BLOCKED, f"Failed on Credit Card PII: {q}"

    def test_false_positive_pii(self):
        """Ensure normal numbers aren't flagged as PII."""
        safe_queries = [
            "What is the expense ratio?",  # No numbers
            "I want to invest 10000 rupees.",  # 5 digits
            "The NAV is 123.45.",  # Decimal
            "Are there any 12 month lock-in periods?"  # 2 digits
        ]
        for q in safe_queries:
            assert QueryGuard.check_query(q) == QueryType.FACTUAL, f"False positive on safe query: {q}"
