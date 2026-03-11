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

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007BFF; color: white; font-weight: bold; }
    .stAlert { margin-top: 10px; }
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
    text = re.sub(r'\.html|\.php|\.aspx', '', text)
    label = text.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

def get_smart_cluster(label):
    label_up = label.upper()
    clusters = ['LOAN', 'SUNSCREEN', 'SERUM', 'COSMETICS', 'SHAMPOO', 'SKINCARE', 'LIPSTICK', 'MAKEUP']
    for c in clusters:
        if c in label_up: return c.title()
    words = label.split()
    return f"{words[0].title()} {words[1].title()}" if len(words) >= 2 else label.title()

# --- PARSING LOGIC ---
def extract_urls_from_raw_xml(xml_content):
    """Extracts all <loc> tags from a string of XML content."""
    soup = BeautifulSoup(xml_content, 'xml')
    return [loc.text.strip() for loc in soup.find_all('loc')]

def get_urls_via_request(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return extract_urls_from_raw_xml(response.content)
        elif response.status_code == 403:
            st.error("🚫 Access Denied (403): This website is blocking automated requests. Please use the 'Paste Raw XML' tab below.")
        else:
            st.error(f"Error: Received status code {response.status_code}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return []

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
            if len(links) > 1: doc.add_heading(group, level=2)
            for text, link in links:
                p = doc.add_paragraph(style='List Bullet')
                add_hyperlink(p, text, link)
    bio = io.BytesIO(); doc.save(bio); bio.seek(0)
    return bio

# --- APP UI ---
st.title("🏗️ Sitemap Architect Pro")
st.write("Professional categorization for all websites, including high-security e-commerce.")

tab1, tab2, tab3 = st.tabs(["🔗 XML URL", "📄 Paste Raw XML", "📝 Naked URLs"])

final_urls = []
domain_name = "Website"

with tab1:
    xml_url = st.text_input("Enter Sitemap URL")
    st.caption("Works for most sites. If you get a 403 error, use Tab 2.")

with tab2:
    raw_xml_content = st.text_area("Paste the XML Code here", height=200, help="Visit the sitemap URL in your browser, copy everything (Ctrl+A), and paste it here.")
    st.info("💡 Use this for Nykaa, Amazon, or sites that block automated access.")

with tab3:
    naked_urls = st.text_area("Paste simple URL list (one per line)", height=200)

if st.button("Generate Professional Sitemap"):
    if tab1 and xml_url:
        domain_name = urlparse(xml_url).netloc
        final_urls = get_urls_via_request(xml_url)
    
    if not final_urls and raw_xml_content:
        domain_name = "Manual-Entry"
        final_urls = extract_urls_from_raw_xml(raw_xml_content)
        
    if not final_urls and naked_urls:
        final_urls = [l.strip() for l in naked_urls.split('\n') if l.strip()]
        domain_name = urlparse(final_urls[0]).netloc if final_urls else "List"

    if final_urls:
        if len(final_urls) > 3000:
            st.warning("Large sitemap detected. Processing first 3000 links.")
            final_urls = final_urls[:3000]
            
        tree = organize_urls(final_urls)
        docx_data = create_docx(tree, domain_name)
        
        st.success(f"Successfully organized {len(final_urls)} links!")
        st.download_button(label="📥 Download .docx Sitemap", data=docx_data, file_name=f"Sitemap_{domain_name}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        st.warning("No URLs found to process. Please check your input.")
