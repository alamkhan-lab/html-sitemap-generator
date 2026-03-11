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

# --- REFINED LABEL EXTRACTION ---
def get_meaningful_label(url):
    path = urlparse(url).path.strip('/')
    if not path: return "Home"
    segments = path.split('/')
    ignore_list = ['c', 'p', 'v', 'cat', 'products', 'collections', 'category', 'brands']
    
    for seg in reversed(segments):
        if seg.isdigit() or seg.lower() in ignore_list or len(seg) < 2:
            continue
        return seg.replace('-', ' ').replace('_', ' ').strip().title()
    return "Link"

def get_smart_cluster(label, section_name):
    """
    Prevents creating a cluster that is identical to the section name.
    Example: If Section is 'Bags', don't create a cluster called 'Bags'.
    """
    label_up = label.upper()
    section_up = section_name.upper()
    
    clusters = ['LOAN', 'SUNSCREEN', 'SERUM', 'COSMETICS', 'SHAMPOO', 'SKINCARE', 'LIPSTICK', 'MAKEUP', 'BAGS', 'FASHION']
    
    for c in clusters:
        if c in label_up and c != section_up:
            return c.title()
            
    # If no specific keyword cluster is found, group by the first word of the label
    words = label.split()
    first_word = words[0] if words else "General"
    
    if first_word.upper() == section_up:
        return "General"
    return first_word

# --- URL EXTRACTION ---
def extract_urls_robust(xml_content):
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode('utf-8', errors='ignore')
    urls = re.findall(r'<loc>(.*?)</loc>', xml_content)
    return list(set(urls))

def organize_urls(urls):
    tree = {}
    for url in urls:
        parsed = urlparse(url)
        path_segments = [s for s in parsed.path.split('/') if s]
        
        # Determine Section (First meaningful folder)
        section = "Main"
        for seg in path_segments:
            if not seg.isdigit() and len(seg) > 2 and seg.lower() not in ['c', 'p']:
                section = seg.replace('-', ' ').title()
                break
        
        page_label = get_meaningful_label(url)
        group = get_smart_cluster(page_label, section)

        if section not in tree: tree[section] = {}
        if group not in tree[section]: tree[section][group] = []
        tree[section][group].append((page_label, url))
    return tree

def create_docx(tree, domain):
    doc = Document()
    doc.add_heading(f'Sitemap Report: {domain}', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for section in sorted(tree.keys()):
        doc.add_heading(section, level=1)
        
        for group, links in tree[section].items():
            # REDUNDANCY CHECK: 
            # 1. Don't show group heading if it's 'General'
            # 2. Don't show group heading if it's the same as the Section
            # 3. Only show group heading if there are multiple items to group
            if group != "General" and group.lower() != section.lower() and len(links) > 1:
                doc.add_heading(group, level=2)
            
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                add_hyperlink(p, text, link)
                
    bio = io.BytesIO(); doc.save(bio); bio.seek(0)
    return bio

# --- UI ---
st.title("🏗️ Sitemap Architect Pro")

tab1, tab2, tab3 = st.tabs(["🔗 XML URL", "📄 Paste Raw XML", "📝 Naked URLs"])
final_urls = []
domain_name = "Website"

with tab1: xml_url = st.text_input("Enter Sitemap URL")
with tab2: raw_xml_content = st.text_area("Paste Raw XML Code", height=200)
with tab3: naked_urls = st.text_area("Paste Naked URL list", height=200)

if st.button("Generate Clean Sitemap"):
    if xml_url:
        domain_name = urlparse(xml_url).netloc
        try:
            r = requests.get(xml_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            final_urls = extract_urls_robust(r.content) if r.status_code == 200 else []
        except: pass
    
    if not final_urls and raw_xml_content:
        final_urls = extract_urls_robust(raw_xml_content)
        domain_name = "Manual-XML"
        
    if not final_urls and naked_urls:
        final_urls = [l.strip() for l in naked_urls.split('\n') if l.strip()]
        domain_name = urlparse(final_urls[0]).netloc if final_urls else "List"

    if final_urls:
        tree = organize_urls(final_urls[:3000])
        docx_data = create_docx(tree, domain_name)
        st.success(f"Organized {len(final_urls)} links into clean categories.")
        st.download_button("📥 Download .docx", docx_data, f"Sitemap_{domain_name}.docx")
    else:
        st.warning("No URLs found. Use Tab 2 for high-security sites like Nykaa.")
