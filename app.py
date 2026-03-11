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
import re

# --- UI CONFIG ---
st.set_page_config(page_title="Sitemap Architect Pro", page_icon="🏗️", layout="centered")

# Custom CSS for a cleaner, "SaaS-like" UI
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    .stTextArea>div>div>textarea { border-radius: 10px; }
    .stTextInput>div>div>input { border-radius: 10px; }
    h1 { color: #1E1E1E; font-family: 'Inter', sans-serif; }
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

def clean_label(slug):
    if not slug: return "Home"
    label = slug.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

def get_smart_group(label):
    # Common e-commerce categories for clustering
    keywords = ['Sunscreen', 'Serum', 'Face Wash', 'Moisturizer', 'Cleanser', 'Cream', 'Oil', 'Toner', 'Shampoo', 'Mask', 'Combo', 'Kit']
    for word in keywords:
        if word.lower() in label.lower():
            return word
    # Fallback to the first word of the slug if no keyword matches
    words = label.split()
    return words[0] if words else "General"

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
        path = parsed.path.strip('/')
        segments = path.split('/')
        
        # Determine Top Category (e.g., Collections, Products, Pages)
        top_cat = clean_label(segments[0]) if segments[0] else "Main Pages"
        
        # Determine Smart Group within that category
        if len(segments) > 1:
            full_label = clean_label(segments[-1])
            group_name = get_smart_group(full_label)
        else:
            full_label = top_cat
            group_name = "General"

        if top_cat not in tree: tree[top_cat] = {}
        if group_name not in tree[top_cat]: tree[top_cat][group_name] = []
        tree[top_cat][group_name].append((full_label, url))
    return tree

def create_docx(tree, domain):
    doc = Document()
    header = doc.add_heading(f'Website Sitemap: {domain}', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for top_cat, groups in tree.items():
        doc.add_heading(top_cat, level=1)
        for group_name, links in groups.items():
            if group_name != "General":
                doc.add_heading(group_name, level=2)
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                add_hyperlink(p, text, link)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- APP INTERFACE ---
st.title("🏗️ Sitemap Architect")
st.write("Convert website structures into professional, hyperlinked Word documents.")

# TABS FOR INPUT OPTIONS
tab1, tab2 = st.tabs(["🔗 XML Sitemap URL", "📄 Paste Naked URLs"])

urls_to_process = []
domain_display = "Generated-Sitemap"

with tab1:
    xml_input = st.text_input("Enter XML URL (e.g., https://site.com/sitemap.xml)")
    if xml_input:
        domain_display = urlparse(xml_input).netloc

with tab2:
    text_input = st.text_area("Paste one URL per line:", height=200, placeholder="https://site.com/page-1\nhttps://site.com/page-2")
    if text_input:
        lines = text_input.split('\n')
        if lines:
            domain_display = urlparse(lines[0]).netloc

# PROCESS BUTTON
if st.button("Generate & Download Sitemap"):
    if tab1 and xml_input:
        with st.spinner("Fetching XML..."):
            urls_to_process = parse_xml(xml_input)
    elif tab2 and text_input:
        urls_to_process = [u.strip() for u in text_input.split('\n') if u.strip()]

    if urls_to_process:
        tree = organize_urls(urls_to_process)
        docx_data = create_docx(tree, domain_display)
        
        st.success(f"Successfully categorized {len(urls_to_process)} links.")
        st.download_button(
            label="📥 Download .docx Sitemap",
            data=docx_data,
            file_name=f"Sitemap_{domain_display.replace('.', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        st.error("Please provide a valid XML URL or a list of URLs.")

st.markdown("---")
st.caption("Instructions: Use the XML tab for automated crawling or the Paste tab for custom lists. The output is a formatted Word doc with clickable anchor text.")
