# utils.py

import re
from fpdf import FPDF
from io import BytesIO
from PIL import Image

from fpdf import FPDF
import re
from io import BytesIO
from PIL import Image

def _clean_markdown_line(line: str) -> str:
    """
    Remove leading/trailing markdown artifacts:
      - headings (#, ##, ###)
      - list markers (*, -, +)
      - horizontal rules (---)
      - bold/italic markers (*, **, __)
    This is a very simple cleaner; you can extend it if needed.
    """
    # Remove horizontal rules
    if re.fullmatch(r"\s*[-*_]{3,}\s*", line):
        return ""
    # Strip leading hashes (e.g. "# Title")
    line = re.sub(r"^#{1,6}\s*", "", line)
    # Strip leading list bullets ("*", "-", "+")
    line = re.sub(r"^[\*\-\+]\s*", "", line)
    # Remove leftover bold/italic markers
    line = line.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    return line.strip()

def generate_adr_pdf(adr_text: str, images: list) -> FPDF:
    """
    Create a PDF from the raw ADR markdown text and a list of image filepaths/URLs.
    Returns an FPDF instance (you can then call .output(<BytesIO>) on it).
    """

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Split the ADR into lines and clean each line
    lines = adr_text.splitlines()
    SECTION_TITLES = [
        "Title",
        "ADR Number",
        "Status",
        "Date",
        "Deciders",
        "Superseded by",
        "Context",
        "Decision",
        "Consequences",
        "Alternatives Considered",
        "Related Decisions"
    ]

    MAX_LINE_LENGTH = 100  # max characters per line before forcing wrap

    MAX_LINE_LENGTH = 100  # max characters per line before forcing wrap

    SECTION_TITLES = [
        "Title",
        "ADR Number",
        "Status",
        "Date",
        "Deciders",
        "Context",
        "Decision",
        "Consequences",
        "Alternatives Considered",
        "Related Decisions"
    ]

    SUBLABEL_PATTERN = r"^(System Type|Functional Requirements|Non-Functional Requirements|Architecture Preference|Prior Discussion|Project Description):"

    for raw_line in lines:
        clean = _clean_markdown_line(raw_line).strip()

        if not clean:
            pdf.ln(4)
            continue

        # Wrap long unbreakable strings
        if len(clean) > MAX_LINE_LENGTH and " " not in clean:
            clean = "\n".join([clean[i:i+MAX_LINE_LENGTH] for i in range(0, len(clean), MAX_LINE_LENGTH)])

        # Bold only section headers (no colon, or trim colon)
        stripped_clean = clean.replace("**", "").rstrip(":")
        if stripped_clean in SECTION_TITLES:
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, stripped_clean, ln=True)
            pdf.set_font("Arial", "", 12)
            continue

        # Check for sub-labels like "System Type: ..."
        if re.match(SUBLABEL_PATTERN, clean):
            label, value = clean.split(":", 1)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(50, 6, f"{label.strip()}:", ln=0)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 6, value.strip(), ln=True)
            continue

        # Normal body text
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 6, clean)
        pdf.ln(1)


        # If there are images, embed them one by one (scaled to page width)
    for img_obj in images:
        try:
            # If img_obj is a URL, you would first download it. 
            # Here let's assume it's either a local path or a PIL Image instance.

            if isinstance(img_obj, str):
                # local filepath
                img = Image.open(img_obj)
            elif isinstance(img_obj, Image.Image):
                img = img_obj
            else:
                continue

            # Save to a temporary in-memory buffer at a reasonable JPEG quality
            buf = BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            buf.seek(0)

            # Calculate width to fit page margins (A4 width=210mm; left+right margins=15mm each)
            max_width = pdf.w - 30  
            # Maintain aspect ratio
            img_w_px, img_h_px = img.size
            dpi = img.info.get("dpi", (72, 72))[0]  # fallback if no DPI
            # Convert pixels → mm approximately: 1 inch ≈ 25.4 mm
            width_mm = img_w_px / dpi * 25.4
            height_mm = img_h_px / dpi * 25.4
            scale = min(1.0, max_width / width_mm)
            final_w = width_mm * scale
            final_h = height_mm * scale

            # Insert image (centered horizontally)
            x = (pdf.w - final_w) / 2
            pdf.image(buf, x=x, y=None, w=final_w)
            pdf.ln(8)

        except Exception:
            # If embedding fails, just skip
            continue

    return pdf
