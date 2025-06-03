import re
import textwrap
from fpdf import FPDF, XPos
from io import BytesIO
from PIL import Image
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & pictographs
    "\U0001F680-\U0001F6FF"  # Transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002700-\U000027BF"  # Dingbats
    "\U0001F900-\U0001F9FF"  # Supplemental symbols
    "\U0001FA70-\U0001FAFF"  # Extended symbols
    "\u200d"                 # Zero-width joiner
    "\u2640-\u2642"          # Gender symbols
    "\u2600-\u2B55"          # Misc symbols
    "]+", flags=re.UNICODE
)
def _clean_markdown_line_chat(line: str) -> str:
    # Remove horizontal rules like --- or ***
    if re.fullmatch(r"\s*[-*_]{3,}\s*", line):
        return ""

    # Remove markdown headers and bullets
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^[\*\-\+]\s*", "", line)

    # Remove leading question marks and optional spaces (e.g. "??? ", "? ")
    line = re.sub(r"^\?+\s*", "", line)

    # Remove bold/italic markdown formatting
    line = line.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
  #  Remove emojis
    line = emoji_pattern.sub(r'', line)
    # Final strip
    return line.strip()


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
        
def add_linked_multicell(pdf, text, url, max_width):
    """
    Print wrapped text with pdf.multi_cell and add a clickable link over it.
    """
    # Save current position
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    # Print text with multi_cell (wraps text)
    pdf.set_text_color(0, 0, 255)
    pdf.multi_cell(max_width, 6, f"- {text}", ln=1)
    
    # Calculate height of the printed text block
    y_end = pdf.get_y()
    height = y_end - y_start
    
    # Add clickable link rectangle over the text
    pdf.link(x_start, y_start, max_width, height, url)

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

import re

def generate_chat_pdf(chat_history) -> FPDF:
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    number_list_pattern = re.compile(r"^\s*(\d+)[\.\)]\s+(.+)")
    print(chat_history)

    # Regex to extract link text and URL from your source format
    link_pattern = re.compile(r'Source \d+:\s*<a href="([^"]+)"[^>]*>([^<]+)</a>')

    def render_paragraphs(text: str):
        for para in text.split("\n\n"):
            lines = para.strip().splitlines()
            for line in lines:
                line = _clean_markdown_line_chat(line)
                match = number_list_pattern.match(line)
                if match:
                    index, content = match.groups()
                    formatted = f"{index}. {content.strip()}"
                    safe_multicell(pdf, f"   {formatted}", available_width)
                elif line:
                    safe_multicell(pdf, line, available_width)
            pdf.ln(3)  # Space between paragraphs

    for idx, (user_msg, ai_msg) in enumerate(chat_history, start=1):
        # --- User Message ---
        if user_msg:
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(33, 33, 255)
            safe_multicell(pdf, "User:", available_width)

            pdf.set_font("Arial", "", 12)
            pdf.set_text_color(0, 0, 0)
            render_paragraphs(user_msg)

        # --- AI Message ---
        if ai_msg and isinstance(ai_msg, dict) and "text" in ai_msg:
            ai_text = ai_msg["text"]
            if ai_text:
                pdf.set_font("Arial", "B", 12)
                pdf.set_text_color(0, 128, 0)
                safe_multicell(pdf, "AI:", available_width)

                pdf.set_font("Arial", "", 12)
                pdf.set_text_color(0, 0, 0)
                render_paragraphs(ai_text)

            # Add images if any
            images = ai_msg.get("images", [])
            for img_path in images:
                try:
                    img = Image.open(img_path)
                    img_width, img_height = img.size

                    img_width_mm = img_width * 0.264583
                    img_height_mm = img_height * 0.264583

                    max_width = available_width
                    if img_width_mm > max_width:
                        scale = max_width / img_width_mm
                        img_width_mm = max_width
                        img_height_mm = img_height_mm * scale

                    if pdf.get_y() + img_height_mm > pdf.page_break_trigger:
                        pdf.add_page()

                    pdf.image(img_path, w=img_width_mm, h=img_height_mm)
                    pdf.ln(5)
                except Exception as e:
                    safe_multicell(pdf, f"[Failed to load image: {img_path}]", available_width)

            # Add sources if any
            sources = ai_msg.get("sources", [])
            if sources:
                pdf.set_font("Arial", "I", 10)
                pdf.set_text_color(100, 100, 100)
                safe_multicell(pdf, "Sources:", available_width)

                for source in sources:
                    match = link_pattern.search(source)
                    if match:
                        url, text = match.groups()
                        add_linked_multicell(pdf, text, url, available_width)
                    else:
                        pdf.set_text_color(100, 100, 100)
                        safe_multicell(pdf, f"- {source}", available_width)

                pdf.ln(5)

        pdf.ln(2)

    pdf.set_text_color(0, 0, 0)
    return pdf
