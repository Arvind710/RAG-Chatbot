import pytest
from unittest.mock import patch, MagicMock
from src.ingestion.scraper import fetch_html, fetch_with_requests, is_js_rendered
import requests

@patch('src.ingestion.scraper.requests.get')
def test_fetch_valid_url(mock_get):
    # E-1.1: Fetch valid URL
    mock_response = MagicMock()
    mock_response.text = "<html><body>" + "A" * 15000 + "</body></html>"
    mock_get.return_value = mock_response
    
    html = fetch_with_requests("https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth")
    assert len(html) > 10000

@patch('src.ingestion.scraper.requests.get')
def test_handle_404(mock_get):
    # E-1.2: Handle 404
    mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found")
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_with_requests("https://groww.in/mutual-funds/nonexistent-fund")

@patch('src.ingestion.scraper.requests.get')
def test_handle_network_timeout(mock_get):
    # E-1.3: Handle network timeout
    mock_get.side_effect = requests.exceptions.Timeout("Read timed out.")
    with pytest.raises(requests.exceptions.Timeout):
        fetch_with_requests("https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth")

@patch('src.ingestion.scraper.fetch_with_playwright')
@patch('src.ingestion.scraper.fetch_with_requests')
def test_js_rendered_fallback(mock_requests, mock_playwright):
    # E-1.4: JS-rendered fallback
    # Mock requests to return a very small HTML body to trigger is_js_rendered
    mock_requests.return_value = "<html><body><div id='root'></div></body></html>"
    mock_playwright.return_value = "<html><body><h1>Real Content</h1></body></html>"
    
    html = fetch_html("https://example.com/js-page")
    assert mock_playwright.called
    assert "Real Content" in html

def test_is_js_rendered():
    # Empty or small react roots should trigger JS fallback
    html1 = "<html><body><div id='root'></div></body></html>"
    assert is_js_rendered(html1) == True
    
    html2 = "<html><body>" + "Some solid content that is fairly long and has useful words. " * 20 + "</body></html>"
    assert is_js_rendered(html2) == False
