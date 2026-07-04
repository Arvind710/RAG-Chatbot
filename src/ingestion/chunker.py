"""Module for semantic chunking of cleaned mutual fund text."""
import os
import glob
import json
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base URLs for mapping
SCHEME_URLS = {
    "HDFC Gold ETF Fund of Fund Direct Plan Growth": "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "HDFC Large Cap Fund Direct Growth": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "HDFC Small Cap Fund Direct Growth": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "HDFC Silver ETF FoF Direct Growth": "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "HDFC Mid Cap Fund Direct Growth": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
}

def clean_footer(lines: List[str]) -> List[str]:
    """Truncate everything after the first occurrence of 'Contact Us' or 'Download the App'."""
    for i, line in enumerate(lines):
        if line.strip() in ["Contact Us", "Download the App"]:
            return lines[:i]
    return lines

def extract_tables_and_text(section_text: str) -> List[Dict[str, str]]:
    """Separates a section into table chunks and text chunks."""
    lines = section_text.split('\n')
    chunks = []
    current_text = []
    current_table = []
    in_table = False
    
    for line in lines:
        if line.strip().startswith('|'):
            if not in_table:
                in_table = True
                if current_text:
                    text_str = '\n'.join(current_text).strip()
                    if text_str:
                        chunks.append({'type': 'text', 'content': text_str})
                    current_text = []
            current_table.append(line)
        else:
            if in_table:
                in_table = False
                table_str = '\n'.join(current_table).strip()
                if table_str:
                    chunks.append({'type': 'table', 'content': table_str})
                current_table = []
            current_text.append(line)
            
    if current_text:
        text_str = '\n'.join(current_text).strip()
        if text_str:
            chunks.append({'type': 'text', 'content': text_str})
    if current_table:
        table_str = '\n'.join(current_table).strip()
        if table_str:
            chunks.append({'type': 'table', 'content': table_str})
            
    return chunks

def filter_fund_management_text(text: str) -> str:
    """Removes the noisy list of other managed funds from the fund management section."""
    lines = text.split('\n')
    filtered = []
    for line in lines:
        # Most noise lines are just other scheme names starting with HDFC
        if line.strip().startswith("HDFC ") and "Fund management" not in line:
            continue
        filtered.append(line)
    return '\n'.join(filtered)

def process_file(filepath: str, text_splitter: RecursiveCharacterTextSplitter) -> List[Dict[str, Any]]:
    """Process a single cleaned JSON file and split it into semantic chunks."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.splitlines()
    if not lines:
        return []
        
    lines = clean_footer(lines)
    
    # Extract metadata
    scheme_name = lines[0].split(' - ')[0].strip()
    source_url = SCHEME_URLS.get(scheme_name, "")
    
    # Extract scrape_date from filename (e.g., hdfc-large-cap..._1783089739.txt)
    filename = os.path.basename(filepath)
    try:
        timestamp_str = filename.split('_')[-1].replace('.txt', '')
        # We just store the timestamp string or format it
        scrape_date = timestamp_str
    except:
        scrape_date = "unknown"
        
    # Find section landmarks
    landmarks = {
        'holdings': -1,
        'min_investment': -1,
        'returns': -1,
        'similar_funds': -1,
        'fund_management': -1,
        'fund_info': -1
    }
    
    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith("Holdings (") and landmarks['holdings'] == -1:
            landmarks['holdings'] = i
        elif line_strip == "Minimum investments" and landmarks['min_investment'] == -1:
            landmarks['min_investment'] = i
        elif line_strip == "Annualised returns" and landmarks['returns'] == -1:
            landmarks['returns'] = i
        elif line_strip == "Compare similar funds" and landmarks['similar_funds'] == -1:
            landmarks['similar_funds'] = i
        elif line_strip == "Fund management" and landmarks['fund_management'] == -1:
            landmarks['fund_management'] = i
        elif line_strip == "About" and landmarks['fund_info'] == -1:
            landmarks['fund_info'] = i
            
    # Create sorted list of boundaries
    boundaries = []
    for name, idx in landmarks.items():
        if idx != -1:
            boundaries.append((idx, name))
            
    boundaries.sort(key=lambda x: x[0])
    
    # Extract section content
    sections = {}
    
    # Overview is from start to first boundary
    first_boundary = boundaries[0][0] if boundaries else len(lines)
    sections['overview'] = '\n'.join(lines[:first_boundary])
    
    for i in range(len(boundaries)):
        start_idx = boundaries[i][0]
        section_name = boundaries[i][1]
        end_idx = boundaries[i+1][0] if i + 1 < len(boundaries) else len(lines)
        sections[section_name] = '\n'.join(lines[start_idx:end_idx])
        
    # Clean fund_management
    if 'fund_management' in sections:
        sections['fund_management'] = filter_fund_management_text(sections['fund_management'])
        
    final_chunks = []
    
    for section_type, sec_content in sections.items():
        if not sec_content.strip():
            continue
            
        parts = extract_tables_and_text(sec_content)
        
        for part in parts:
            context_prefix = f"Scheme: {scheme_name}\nSection: {section_type.replace('_', ' ').title()}\n\n"
            if part['type'] == 'table':
                # Atomic table chunk
                chunk_data = {
                    'content': context_prefix + part['content'],
                    'metadata': {
                        'source_url': source_url,
                        'scheme_name': scheme_name,
                        'section_type': section_type,
                        'scrape_date': scrape_date,
                        'has_table': True
                    }
                }
                final_chunks.append(chunk_data)
            else:
                # Text chunk, split if > 500
                text_content = part['content']
                if len(text_content) > 500:
                    split_texts = text_splitter.split_text(text_content)
                    for st in split_texts:
                        if st.strip():
                            final_chunks.append({
                                'content': context_prefix + st.strip(),
                                'metadata': {
                                    'source_url': source_url,
                                    'scheme_name': scheme_name,
                                    'section_type': section_type,
                                    'scrape_date': scrape_date,
                                    'has_table': False
                                }
                            })
                else:
                    final_chunks.append({
                        'content': context_prefix + text_content,
                        'metadata': {
                            'source_url': source_url,
                            'scheme_name': scheme_name,
                            'section_type': section_type,
                            'scrape_date': scrape_date,
                            'has_table': False
                        }
                    })
                    
    return final_chunks

def run_chunker():
    """Run the chunker on all cleaned data files."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cleaned_dir = os.path.join(base_dir, "data", "cleaned")
    processed_dir = os.path.join(base_dir, "data", "processed")
    
    os.makedirs(processed_dir, exist_ok=True)
    
    cleaned_files = glob.glob(os.path.join(cleaned_dir, "*.txt"))
    if not cleaned_files:
        logger.warning(f"No cleaned text files found in {cleaned_dir}")
        return
        
    logger.info(f"Found {len(cleaned_files)} cleaned files to chunk.")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " "]
    )
    
    total_chunks = 0
    for filepath in cleaned_files:
        filename = os.path.basename(filepath)
        json_filename = filename.replace(".txt", ".json")
        json_filepath = os.path.join(processed_dir, json_filename)
        
        try:
            chunks = process_file(filepath, text_splitter)
            
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Successfully chunked {filename} -> {len(chunks)} chunks")
            total_chunks += len(chunks)
        except Exception as e:
            logger.error(f"Failed to chunk {filename}: {e}", exc_info=True)
            
    logger.info(f"Chunking complete. Total chunks generated: {total_chunks}")

if __name__ == "__main__":
    run_chunker()
