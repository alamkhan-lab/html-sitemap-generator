import streamlit as st
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import qn
from docx.oxml import OxmlElement
from urllib.parse import urlparse
import io
import collections

# --- UI CONFIG ---
st.set_page_config(page_title="Sitemap Architect Pro", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007BFF; color: white; font-weight: bold; }
    .stTextArea textarea { border-radius: 10px; }
    .stTextInput input { border-radius: 10px; }
    h1 { color: #1E1E1E; }
    </style>
    """, unsafe_allow_html=True)

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
    # Remove domain-like strings and file extensions
    text = re.sub(r'\.html|\.php|\.aspx', '', text)
    label = text.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

import re

def get_smart_cluster(label):
    """
    Groups by subject rather than exact match.
    Example: 'Personal Loan Eligibility' -> 'Personal Loan'
    """
    label = label.upper()
    
    # Priority BFSI & E-commerce Subject Clusters
    clusters = [
        'PERSONAL LOAN', 'HOME LOAN', 'BUSINESS LOAN', 'GOLD LOAN', 'CAR LOAN', 'MOBILE LOAN',
        'CREDIT CARD', 'DEBIT CARD', 'FIXED DEPOSIT', 'INSURANCE', 'INVESTMENT',
        'SUNSCREEN', 'FACE WASH', 'SERUM', 'MOISTURIZER', 'CALCULATOR'
    ]
    
    for c in clusters:
        if c in label:
            return c.title()
    
    # If no keyword matches, take the first TWO words as the category
    words = label.split()
    if len(words) >= 2:
        return f"{words[0].title()} {words[1].title()}"
    elif len(words) == 1:
        return words[0].title()
    
    return "General"

def parse_xml(xml_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(xml_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'xml')
        return [loc.text for loc in soup.find_all('loc')]
    except:
        return []

def organize_urls(urls):
    tree = {}
    for url in urls:
        url = url.strip()
        if not url: continue
        parsed = urlparse(url)
        path_segments = [s for s in parsed.path.split('/') if s]
        
        # 1. Determine Section (Top Level folder like /loans/ or /products/)
        section = clean_label(path_segments[0]) if path_segments else "Main Pages"
        
        # 2. Determine Page Label
        page_label = clean_label(path_segments[-1]) if path_segments else "Home"
        
        # 3. Determine Group (The Cluster)
        # We analyze the page label to see what 'Subject' it belongs to
        group = get_smart_cluster(page_label)

        if section not in tree: tree[section] = {}
        if group not in tree[section]: tree[section][group] = []
        
        # Avoid redundancy: If link text is same as group, keep it simple
        tree[section][group].append((page_label, url))
    return tree

def create_docx(tree, domain):
    doc = Document()
    header = doc.add_heading(f'Website Sitemap: {domain}', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Sort sections to keep 'Main Pages' or 'Home' at top
    for section in sorted(tree.keys()):
        doc.add_heading(section, level=1)
        
        for group, links in tree[section].items():
            # Only add a sub-heading if it's not a generic single link
            if len(links) > 1 or group not in section:
                doc.add_heading(group, level=2)
            
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                add_hyperlink(p, text, link)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- UI ---
st.title("🏗️ Sitemap Architect Pro")
st.write("Professional categorization engine for BFSI, E-commerce, and Corporate sites.")

tab1, tab2 = st.tabs(["🔗 XML Sitemap URL", "📄 Paste Naked URLs"])

urls_to_process = []
domain_name = "Website"

with tab1:
    xml_input = st.text_input("Sitemap XML Link", placeholder="https://bank.com/sitemap.xml")
    if xml_input: domain_name = urlparse(xml_input).netloc

with tab2:
    text_input = st.text_area("Paste URLs (one per line)", height=200)
    if text_input: 
        lines = [l for l in text_input.split('\n') if l.strip()]
        if lines: domain_name = urlparse(lines[0]).netloc

if st.button("Generate Structured Sitemap"):
    if xml_input and not urls_to_process:
        with st.spinner("Analyzing XML structure..."):
            urls_to_process = parse_xml(xml_input)
    elif text_input:
        urls_to_process = [l.strip() for l in text_input.split('\n') if l.strip()]

    if urls_to_process:
        tree = organize_urls(urls_to_process)
        docx_data = create_docx(tree, domain_name)
        
        st.success(f"Categorized {len(urls_to_process)} URLs into intelligent clusters.")
        st.download_button(
            label="📥 Download Structured Doc",
            data=docx_data,
            file_name=f"Sitemap_{domain_name.replace('.', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        st.error("No URLs found to process.")
