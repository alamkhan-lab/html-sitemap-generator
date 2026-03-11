import streamlit as st
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import qn
from docx.oxml import OxmlElement
from urllib.parse import urlparse
import io
import re

# --- UI CONFIG ---
st.set_page_config(page_title="Sitemap Architect Pro", page_icon="🏗️")

# --- HYPERLINK HELPER ---
def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color'); c.set(qn('w:val'), '0563C1')
    rPr.append(c)
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single')
    rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement('w:t'); t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def clean_label(text):
    if not text: return ""
    text = re.sub(r'\.html|\.php|\.aspx', '', text)
    label = text.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

def get_smart_cluster(label):
    label_up = label.upper()
    clusters = [
        'LOAN', 'INSURANCE', 'SUNSCREEN', 'SERUM', 'SITEMAP', 'MARKETING', 
        'SEO', 'CASE STUDY', 'SERVICE', 'GUIDE', 'CALCULATOR'
    ]
    for c in clusters:
        if c in label_up: return c.title()
    words = label.split()
    return f"{words[0].title()} {words[1].title()}" if len(words) >= 2 else label.title()

# --- IMPROVED STEALTH FETCHING ---
def get_all_urls_from_sitemap(url, visited_indexes=None):
    if visited_indexes is None: visited_indexes = set()
    if url in visited_indexes: return []
    visited_indexes.add(url)
    
    found_urls = []
    # Advanced headers to bypass Cloudflare/Firewalls
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20, verify=True)
        # Check if we actually got the content
        if response.status_code != 200:
            st.error(f"Access Denied (Status {response.status_code}) for {url}. The site may be blocking automated requests.")
            return []

        # Use 'lxml' or 'html.parser' as fallback for XML namespaces
        soup = BeautifulSoup(response.content, 'xml')
        
        # Search for <loc> tags directly (more reliable than searching for <url> or <sitemap>)
        loc_tags = soup.find_all('loc')
        
        for loc in loc_tags:
            loc_text = loc.text.strip()
            # If the loc points to another XML, it's a sub-sitemap
            if loc_text.endswith('.xml') or 'sitemap' in loc_text.lower():
                if loc_text != url: # Avoid infinite loops
                    found_urls.extend(get_all_urls_from_sitemap(loc_text, visited_indexes))
            else:
                found_urls.append(loc_text)
                
    except Exception as e:
        st.error(f"Error fetching {url}: {str(e)}")
        
    return list(set(found_urls))

def organize_urls(urls):
    tree = {}
    for url in urls:
        parsed = urlparse(url)
        path_segments = [s for s in parsed.path.split('/') if s]
        section = clean_label(path_segments[0]) if path_segments else "Main Pages"
        page_label = clean_label(path_segments[-1]) if path_segments else "Home"
        group = get_smart_cluster(page_label)

        if section not in tree: tree[section] = {}
        if group not in tree[section]: tree[section][group] = []
        tree[section][group].append((page_label, url))
    return tree

def create_docx(tree, domain):
    doc = Document()
    doc.add_heading(f'Sitemap Architect Report: {domain}', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for section in sorted(tree.keys()):
        doc.add_heading(section, level=1)
        for group, links in tree[section].items():
            if len(links) > 1:
                doc.add_heading(group, level=2)
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                add_hyperlink(p, text, link)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- APP UI ---
st.title("🏗️ Sitemap Architect Pro")
st.write("Specialized engine for E-commerce, BFSI, and SEO-heavy sitemaps.")

xml_input = st.text_input("Enter Sitemap URL (e.g., https://www.infidigit.com/page-sitemap.xml)")

if st.button("Build Professional Sitemap"):
    if xml_input:
        domain_name = urlparse(xml_input).netloc
        with st.spinner(f"Connecting to {domain_name}... This may take a moment."):
            final_urls = get_all_urls_from_sitemap(xml_input)
            
            if final_urls:
                # Limit for Word Doc stability
                if len(final_urls) > 3000:
                    st.warning("Very large sitemap. Processing first 3000 links.")
                    final_urls = final_urls[:3000]
                    
                tree = organize_urls(final_urls)
                docx_data = create_docx(tree, domain_name)
                
                st.success(f"Successfully extracted and categorized {len(final_urls)} links!")
                st.download_button(
                    label="📥 Download .docx Sitemap",
                    data=docx_data,
                    file_name=f"Sitemap_{domain_name.replace('.', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error("Could not find any URLs. The website may be blocking the crawler or the XML format is non-standard.")
