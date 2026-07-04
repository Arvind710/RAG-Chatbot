"""
Tests for the generation and formatting pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from groq import RateLimitError

from src.generation.generator import generate_response, answer_query
from src.generation.query_guard import QueryType
from src.utils.formatter import format_response

# 1. Test response format validation
def test_formatter_3_sentences():
    # Provide a 4 sentence response without tables/lists
    long_response = "Sentence one. Sentence two. Sentence three. Sentence four."
    formatted = format_response(long_response, "http://example.com", "2026-07-04")
    
    assert "Sentence four." not in formatted
    assert "Sentence three." in formatted
    assert "Source: http://example.com" in formatted
    assert "Last updated from sources: 2026-07-04" in formatted

def test_formatter_tables_ignored():
    # Responses with tables shouldn't be cut to 3 sentences
    table_response = "Here is the table.\n| Col1 | Col2 |\n|---|---|\n| A | B |\nSentence 5."
    formatted = format_response(table_response)
    assert "| Col1 | Col2 |" in formatted
    assert "Sentence 5." in formatted # not truncated

def test_formatter_no_information():
    response = "I don't have this information."
    formatted = format_response(response, "http://example.com", "2026-07-04")
    assert formatted == "I don't have this information."
    assert "Source:" not in formatted

# 2. Test exponential backoff handles RateLimitError gracefully
@patch("src.generation.generator.client.chat.completions.create")
def test_generate_response_rate_limit_retry(mock_create):
    # Mocking a rate limit error twice, then a success
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Success!"))]
    
    response_mock = MagicMock()
    response_mock.status_code = 429
    error = RateLimitError("Rate limit exceeded", response=response_mock, body=None)
    
    mock_create.side_effect = [error, error, mock_response]
    
    # We should get "Success!" eventually because tenacity retries
    res = generate_response("system", "user")
    assert res == "Success!"
    assert mock_create.call_count == 3

# 3. Test end-to-end with mocked LLM and Retriever
@patch("src.generation.generator.retriever.retrieve")
@patch("src.generation.generator.generate_response")
@patch("src.generation.query_guard.QueryGuard.check_query")
def test_answer_query_factual(mock_check_query, mock_gen, mock_retrieve):
    # Mock factual intent
    mock_check_query.return_value = QueryType.FACTUAL
    
    # Mock retriever chunks
    mock_retrieve.return_value = [
        {
            "content": "The expense ratio is 0.5%.",
            "metadata": {"source_url": "http://groww.in/fund", "scrape_date": "2026-07-01"}
        }
    ]
    
    # Mock LLM generation
    mock_gen.return_value = "The expense ratio is 0.5%."
    
    result = answer_query("What is the expense ratio?")
    
    assert "The expense ratio is 0.5%." in result
    assert "Source: http://groww.in/fund" in result
    assert "Last updated from sources: 2026-07-01" in result

@patch("src.generation.query_guard.QueryGuard.check_query")
def test_answer_query_advisory(mock_check_query):
    mock_check_query.return_value = QueryType.ADVISORY
    result = answer_query("Should I invest in this fund?")
    assert "financial advice" in result
