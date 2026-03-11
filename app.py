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
st.set_page_config(page_title="Pro Sitemap Generator", page_icon="📑")

st.title("📑 Pro HTML Sitemap Generator")
st.info("This version groups similar items (like all 'Sunscreens') and creates clickable hyperlinks.")

# --- HYPERLINK HELPER FUNCTION ---
def add_hyperlink(paragraph, text, url):
    """Adds a clickable hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)

    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    
    # Blue color and underline for the link
    c = OxmlElement('w:color')
    c.set(qn('w:val'), '0563C1')
    rPr.append(c)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    
    new_run.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)

    paragraph._p.append(hyperlink)
    return hyperlink

def clean_label(slug):
    label = slug.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

def get_smart_group(label):
    """Identify a common group name (e.g., 'Sunscreen' for 'Sunscreen for Dry Skin')"""
    keywords = ['Sunscreen', 'Serum', 'Face Wash', 'Moisturizer', 'Cleanser', 'Cream', 'Oil', 'Toner']
    for word in keywords:
        if word.lower() in label.lower():
            return word
    return label.split()[0] if label.split() else "General"

def get_urls_from_xml(xml_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(xml_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'xml')
        return [loc.text for loc in soup.find_all('loc')]
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def organize_urls_smart(urls):
    """Groups URLs based on common keywords found in slugs."""
    tree = {}
    for url in urls:
        path = urlparse(url).path.strip('/')
        segments = path.split('/')
        
        # High Level (e.g., Collections vs Products)
        top_cat = clean_label(segments[0]) if segments else "Main"
        
        # Sub Level grouping logic
        if len(segments) > 1:
            full_label = clean_label(segments[1])
            group_name = get_smart_group(full_label)
        else:
            full_label = top_cat
            group_name = "General"

        if top_cat not in tree: tree[top_cat] = {}
        if group_name not in tree[top_cat]: tree[top_cat][group_name] = []
        
        tree[top_cat][group_name].append((full_label, url))
    return tree

def create_pro_docx(tree, domain):
    doc = Document()
    
    # Header
    section = doc.sections[0]
    header = doc.add_heading(f'HTML Sitemap: {domain}', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for top_cat, groups in tree.items():
        doc.add_heading(top_cat, level=1)
        
        for group_name, links in groups.items():
            # Grouping Heading (e.g., "Sunscreen")
            doc.add_heading(group_name, level=2)
            
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                # Use the helper to add a real clickable link
                add_hyperlink(p, text, link)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- APP UI ---
xml_input = st.text_input("Enter XML Sitemap URL:", placeholder="https://codeskin.in/sitemap_collections.xml")

if st.button("Generate Professional Sitemap"):
    if xml_input:
        with st.spinner("Analyzing structure and grouping products..."):
            urls = get_urls_from_xml(xml_input)
            if urls:
                domain = urlparse(xml_input).netloc
                tree = organize_urls_smart(urls)
                docx_data = create_pro_docx(tree, domain)
                
                st.success(f"Organized {len(urls)} links into smart categories.")
                st.download_button(
                    label="📥 Download Structured Sitemap",
                    data=docx_data,
                    file_name=f"Sitemap_{domain}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
