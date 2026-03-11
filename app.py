import streamlit as st
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from urllib.parse import urlparse
import io
import re

# --- UI CONFIG ---
st.set_page_config(page_title="Professional HTML Sitemap Generator", page_icon="🌐")

st.title("🌐 HTML Sitemap Architect")
st.markdown("""
Generate a structured, human-readable HTML sitemap in a **Word Document (.docx)**. 
Ideal for SEO audits and site planning.
""")

# --- FUNCTIONS ---

def clean_label(slug):
    """Turns 'men-running-shoes' into 'Men Running Shoes'"""
    label = slug.replace('-', ' ').replace('_', ' ').strip('/')
    return label.title()

def get_urls_from_xml(xml_url):
    """Fetches and parses URLs from an XML sitemap."""
    try:
        response = requests.get(xml_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    except Exception as e:
        st.error(f"Error fetching XML: {e}")
        return []

def organize_urls(urls):
    """
    Groups URLs into a nested dictionary based on path segments.
    Example: /collections/men-shoes -> { 'Collections': { 'Men Shoes': [url] } }
    """
    tree = {}
    
    for url in urls:
        path = urlparse(url).path.strip('/')
        segments = path.split('/')
        
        if not segments or segments[0] == '':
            category = "Home & Main Pages"
            sub_category = "General"
        else:
            category = clean_label(segments[0])
            sub_category = clean_label(segments[1]) if len(segments) > 1 else "General"
        
        if category not in tree:
            tree[category] = {}
        if sub_category not in tree[category]:
            tree[category][sub_category] = []
            
        # Get a clean title for the link (last part of the URL)
        link_title = clean_label(segments[-1]) if segments[-1] else "Home"
        tree[category][sub_category].append((link_title, url))
        
    return tree

def create_docx(tree, domain_name):
    """Generates the Word Document with styling."""
    doc = Document()
    
    # Title
    title = doc.add_heading(f'Sitemap: {domain_name}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for category, sub_cats in tree.items():
        # Level 1 Heading (e.g., Collections, Products)
        doc.add_heading(category, level=1)
        
        for sub_cat, links in sub_cats.items():
            # Level 2 Heading (e.g., Men Wear, Sale)
            doc.add_heading(sub_cat, level=2)
            
            # List of Links
            for link_text, link_url in links:
                p = doc.add_paragraph(style='List Bullet')
                # Add hyperlink-like styling (Docx doesn't support easy hyperlinking, 
                # so we provide Text + URL for clarity)
                run = p.add_run(f"{link_text}: ")
                run.bold = True
                p.add_run(link_url)

    # Save to buffer
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- MAIN APP UI ---

input_url = st.text_input("Paste your XML Sitemap URL (e.g., https://example.com/sitemap.xml)", "")

if st.button("Generate Sitemap Document"):
    if input_url:
        with st.spinner("Crawling and Organizing URLs..."):
            urls = get_urls_from_xml(input_url)
            
            if urls:
                domain = urlparse(input_url).netloc
                structured_data = organize_urls(urls)
                docx_file = create_docx(structured_data, domain)
                
                st.success(f"Successfully processed {len(urls)} URLs!")
                
                st.download_button(
                    label="📥 Download Sitemap (.docx)",
                    data=docx_file,
                    file_name=f"sitemap_{domain.replace('.', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.warning("No URLs found. Please check the XML link.")
    else:
        st.info("Please enter a URL first.")

st.markdown("---")
st.caption("Tip: This tool groups URLs by their folders (e.g., /collections/, /blog/) to create a hierarchy like Myntra.")
