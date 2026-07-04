"""Module for cleaning raw HTML data from Groww."""
import os
import glob
import logging
from bs4 import BeautifulSoup, NavigableString, Tag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_table_to_markdown(table: Tag) -> str:
    """Converts a BeautifulSoup table tag to a Markdown formatted string."""
    markdown = []
    rows = table.find_all('tr')
    
    for i, row in enumerate(rows):
        # Extract headers or cells
        cols = row.find_all(['th', 'td'])
        row_data = [col.get_text(separator=" ", strip=True).replace("|", "\\|") for col in cols]
        
        if not row_data:
            continue
            
        markdown.append("| " + " | ".join(row_data) + " |")
        
        # Add separator after header
        if i == 0 and table.find('th'):
            markdown.append("|" + "|".join(["---"] * len(row_data)) + "|")
            
    return "\n" + "\n".join(markdown) + "\n"

def clean_html(html_content: str) -> str:
    """
    Cleans raw HTML by removing scripts, styles, navigation, footers, etc.,
    and formatting tables as markdown to preserve tabular data.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Remove unwanted elements
    unwanted_tags = [
        'script', 'style', 'noscript', 'nav', 'footer', 'header', 
        'aside', 'iframe', 'button', 'svg', 'canvas'
    ]
    for tag in soup.find_all(unwanted_tags):
        tag.decompose()
        
    # 2. Heuristic removal of ads, banners, or irrelevant divs by class/id
    # We remove common generic class names that indicate non-content
    unwanted_classes_ids = ['ad', 'banner', 'sidebar', 'menu', 'popup', 'modal', 'cookie', 'overlay']
    for elem in soup.find_all(['div', 'section']):
        if not getattr(elem, 'attrs', None):
            continue
            
        class_list = elem.get('class', [])
        elem_id = elem.get('id', '').lower()
        
        # class_list is a list of strings
        if isinstance(class_list, str):
            class_list = [class_list]
            
        should_remove = False
        for bad in unwanted_classes_ids:
            # Avoid blind substring matching on elem_id (e.g., "ad" in "exitload")
            if elem_id == bad or elem_id.startswith(bad + '-') or elem_id.startswith(bad + '_') or bad in elem_id.split('-') or bad in elem_id.split('_'):
                should_remove = True
                break
            for c in class_list:
                c_lower = c.lower()
                # Match exactly or as a prefix like ad-container or ad_container
                if c_lower == bad or c_lower.startswith(bad + '-') or c_lower.startswith(bad + '_') or bad in c_lower.split('-') or bad in c_lower.split('_'):
                    should_remove = True
                    break
            if should_remove:
                break
                
        if should_remove:
            # Be careful not to remove main content if it has 'modal' or something, 
            # but usually these are safe to remove.
            elem.decompose()
            
    # 3. Convert tables to markdown and replace them in the tree
    for table in soup.find_all('table'):
        md_table = convert_table_to_markdown(table)
        # Create a new string with the markdown and replace the table tag
        table.replace_with(NavigableString(md_table))
        
    # 4. Extract text
    # Using a separator to keep paragraphs distinct
    text = soup.get_text(separator="\n", strip=True)
    
    # 5. Normalize whitespace
    cleaned_lines = []
    for line in text.splitlines():
        clean_line = line.strip()
        if clean_line:
            # Collapse multiple spaces into one
            clean_line = " ".join(clean_line.split())
            cleaned_lines.append(clean_line)
            
    # Return joined text, ensuring tabular markdown isn't completely mangled
    return "\n".join(cleaned_lines)

def run_cleaner():
    """Clean all raw HTML files and save processed text."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    raw_dir = os.path.join(base_dir, "data", "raw")
    cleaned_dir = os.path.join(base_dir, "data", "cleaned")
    
    os.makedirs(cleaned_dir, exist_ok=True)
    
    raw_files = glob.glob(os.path.join(raw_dir, "*.html"))
    if not raw_files:
        logger.warning(f"No HTML files found in {raw_dir}")
        return
        
    logger.info(f"Found {len(raw_files)} raw HTML files to clean.")
    
    for raw_file in raw_files:
        filename = os.path.basename(raw_file)
        cleaned_filename = filename.replace(".html", ".txt")
        cleaned_filepath = os.path.join(cleaned_dir, cleaned_filename)
        
        try:
            with open(raw_file, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            cleaned_text = clean_html(html_content)
            
            with open(cleaned_filepath, "w", encoding="utf-8") as f:
                f.write(cleaned_text)
                
            logger.info(f"Successfully cleaned {filename} -> {cleaned_filename}")
        except Exception as e:
            logger.error(f"Failed to clean {filename}: {e}", exc_info=True)

if __name__ == "__main__":
    run_cleaner()
