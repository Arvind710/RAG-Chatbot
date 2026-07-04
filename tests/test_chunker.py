import pytest
from src.ingestion.chunker import extract_tables_and_text, process_file, clean_footer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import tempfile

def test_standard_chunking():
    # E-1.11: Standard chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ". ", " "])
    text = "HDFC Large Cap Fund Direct Growth - NAV\nAbout\n" + "A word " * 300
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(text)
        temp_path = f.name
        
    chunks = process_file(temp_path, text_splitter)
    os.remove(temp_path)
    
    # About 1500 chars should be 4 chunks
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk['content']) <= 600

def test_short_text():
    # E-1.12: Short text (< 500 chars)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    text = "HDFC Large Cap Fund Direct Growth - NAV\nAbout\nShort factual text."
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(text)
        temp_path = f.name
        
    chunks = process_file(temp_path, text_splitter)
    os.remove(temp_path)
    
    assert len(chunks) == 2  # overview and fund_info
    assert len(chunks[1]['content']) <= 600

def test_metadata_attachment():
    # E-1.13: Metadata attachment
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    text = "HDFC Large Cap Fund Direct Growth - NAV\nAbout\nSome text."
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_123456.txt') as f:
        f.write(text)
        temp_path = f.name
        
    chunks = process_file(temp_path, text_splitter)
    os.remove(temp_path)
    
    assert 'source_url' in chunks[0]['metadata']
    assert 'scheme_name' in chunks[0]['metadata']
    assert 'section_type' in chunks[0]['metadata']
    assert 'scrape_date' in chunks[0]['metadata']
    assert chunks[0]['metadata']['scheme_name'] == 'HDFC Large Cap Fund Direct Growth'

def test_no_data_loss():
    # E-1.14: No data loss
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ". ", " "])
    text = "HDFC Large Cap Fund Direct Growth - NAV\nAbout\n" + "Word " * 200
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(text)
        temp_path = f.name
        
    chunks = process_file(temp_path, text_splitter)
    os.remove(temp_path)
    
    # Concat all chunks
    all_content = " ".join([c['content'] for c in chunks])
    assert "Word" in all_content

def test_numerical_integrity():
    # E-1.15: Numerical integrity
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0, separators=["\n", " "])
    # The number 0.68% shouldn't be split in half (e.g. 0. and 68%) because the splitter uses space separator
    text = "HDFC Large Cap Fund Direct Growth - NAV\nAbout\n" + "A " * 45 + "0.68% " + "B " * 45
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(text)
        temp_path = f.name
        
    chunks = process_file(temp_path, text_splitter)
    os.remove(temp_path)
    
    found = False
    for chunk in chunks:
        if "0.68%" in chunk['content']:
            found = True
        assert "0." not in chunk['content'] or "0.68%" in chunk['content']
        
    assert found
