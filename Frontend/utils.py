# utils.py

import re
from fpdf import FPDF
from io import BytesIO
from PIL import Image

# Utility: Clean text
def clean_text(text):
    # Add newline before each numbered point (except at the beginning)
    text = re.sub(r'(?<!^)(\s*)(\d+\.)', r'\n\2', text)
    # Add newline before each '*' bullet and remove the '*' character
    text = re.sub(r'(?<!^)(\s*)\*', r'\n', text)
    # Normalize whitespace and remove non-ASCII characters
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()
def generate_adr_pdf(adr_text, images=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Architecture Decision Record (ADR)", ln=1, align='C')
    pdf.ln(10)

    sections = adr_text.split("## ")
    pdf.set_font("Arial", size=12)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().splitlines()
        print(section)
        print(lines)
        if len(lines) < 1:
            continue  # Skip sections without content

        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        
        if not body.strip() or all(line.strip() in ("", "#") for line in body.splitlines()):
            continue

        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, txt=heading, ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(190, 10, txt=clean_text(body))
        pdf.ln(5)

    if images:
        for img_path in images:
            try:
                img = Image.open(img_path)
                img = img.resize((500, 400))
                img_io = BytesIO()
                img.save(img_io, format='PNG')
                img_io.seek(0)
                pdf.image(img_io, w=150)
                pdf.ln(5)
            except Exception as e:
                print(f"Error loading image: {img_path}", e)

    return pdf