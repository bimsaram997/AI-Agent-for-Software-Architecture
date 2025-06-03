import re
import textwrap
from fpdf import FPDF, XPos
from io import BytesIO
from PIL import Image

def _clean_markdown_line(line: str) -> str:
    if re.fullmatch(r"\s*[-*_]{3,}\s*", line):
        return ""
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^[\*\-\+]\s*", "", line)
    line = line.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    return line.strip()

def _force_break_long_words(text, max_chars=80):
    # Insert soft breaks into long words (no spaces)
    def break_word(word):
        return '\n'.join(word[i:i+max_chars] for i in range(0, len(word), max_chars))

    return ' '.join(break_word(w) if len(w) > max_chars else w for w in text.split())

def safe_multicell(pdf, text, available_width):
    try:
        # Remove unsupported characters
        text = text.encode('latin-1', 'replace').decode('latin-1')

        # Ensure no single word is longer than available width
        text = _force_break_long_words(text, max_chars=90)

        # Wrap manually to avoid internal FPDF word breaking issues
        wrapped_lines = textwrap.wrap(text, width=90, break_long_words=True)

        for line in wrapped_lines:
            if pdf.get_string_width(line) >= available_width:
                parts = [line[i:i+90] for i in range(0, len(line), 90)]
                for p in parts:
                    pdf.multi_cell(0, 6, txt=p, new_x=XPos.LEFT)
            else:
                pdf.multi_cell(0, 6, txt=line, new_x=XPos.LEFT)

    except Exception as e:
        print(f"[ERROR] Rendering line failed: {text[:30]}... | {e}")
        pdf.multi_cell(0, 6, txt="[Line skipped due to formatting error]")

def generate_adr_pdf(adr_text: str, images: list) -> FPDF:
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    for raw_line in adr_text.splitlines():
        clean = _clean_markdown_line(raw_line)

        if not clean:
            pdf.ln(4)
            continue

        if re.match(r"^(Context|Decision|Consequences|Alternatives Considered|Related Decisions):", clean):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 8, txt=clean[:200], ln=True)  # avoid line too long
            pdf.set_font("Arial", size=12)
            continue

        safe_multicell(pdf, clean, available_width)
    print(images)
    for img_obj in images:
        try:
            if isinstance(img_obj, str):
                img = Image.open(img_obj)
            elif isinstance(img_obj, Image.Image):
                img = img_obj
            else:
                continue

            buf = BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            buf.seek(0)

            max_width = available_width
            img_w_px, img_h_px = img.size
            dpi = img.info.get("dpi", (72, 72))[0]
            width_mm = img_w_px / dpi * 25.4
            height_mm = img_h_px / dpi * 25.4
            scale = min(1.0, max_width / width_mm)
            final_w = width_mm * scale
            final_h = height_mm * scale

            x = (pdf.w - final_w) / 2
            pdf.image(buf, x=x, y=None, w=final_w)
            pdf.ln(8)

        except Exception as e:
            print(f"[WARNING] Image skipped: {e}")
            continue

    return pdf
