import streamlit as st
import requests
from fpdf import FPDF
import re
from io import BytesIO
from PIL import Image

# Backend endpoints
BACKEND_URL_STRUCTURED = "http://127.0.0.1:8000/structured-query"
BACKEND_URL_OPEN_ENDED = "http://127.0.0.1:8000/query"
BACKEND_URL_ADR = "http://127.0.0.1:8000/generate-adr"

# Page config
st.set_page_config(page_title="AI Software Architect", layout="wide")
st.title("🧠 AI-Powered Software Architecture Assistant")

# Session state initialization
if "stage" not in st.session_state:
    st.session_state.stage = "questions"
if "recommendations" not in st.session_state:
    st.session_state.recommendations = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "clear_input" not in st.session_state:
    st.session_state.clear_input = False
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "adr_text" not in st.session_state:
    st.session_state.adr_text = ""
if "adr_pdf_bytes" not in st.session_state:
    st.session_state.adr_pdf_bytes = None

# Clear input if flag set
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False

# Utility: Clean text
def clean_text(text):
    # Add newline before each numbered point (except at the beginning)
    text = re.sub(r'(?<!^)(\s*)(\d+\.)', r'\n\2', text)
    text = re.sub(r'(?<!^)(\s*)(\*)', r'\n\2', text)
    # Normalize whitespace and remove non-ASCII characters
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()

# Generate ADR-only PDF
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
# Step 1: Questions
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    system_type = st.selectbox(
        "What type of system are you designing?",
        ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
    )

    functional_requirements = st.multiselect(
        "Select your functional requirements",
        ["User authentication and authorization", "File upload/download", "Real-time data processing",
         "Data analytics and reporting", "Payment processing", "Notification system (email/SMS/push)",
         "Multi-language support", "Integration with third-party APIs", "Role-based access control",
         "Search functionality", "CRUD operations (Create, Read, Update, Delete)", "Admin dashboard"]
    )

    non_functional_requirements = st.multiselect(
        "Select your non functional requirements",
        ["High availability", "Auto-scaling", "Load balancing", "Low latency response time",
         "Data encryption at rest", "Data encryption in transit", "Multi-factor authentication (MFA)",
         "Audit logging", "Modular design", "CI/CD support", "Logging and monitoring",
         "API documentation", "Fault tolerance", "Disaster recovery", "Backup and restore",
         "Retry mechanisms", "Cloud-native deployment", "On-premise compatibility", "Multi-region deployment",
         "Containerization (Docker, Kubernetes)", "High-volume data ingestion",
         "Structured and unstructured data support", "Caching layer", "Data warehousing", "Code portability"]
    )

    architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"]
    )

    if st.button("Get Recommendations"):
        with st.spinner("Generating recommendation..."):
            try:
                st.session_state.system_type = system_type
                st.session_state.functional_requirements = functional_requirements
                st.session_state.non_functional_requirements = non_functional_requirements
                st.session_state.architecture_preference = architecture_preference
                response = requests.post(
                    BACKEND_URL_STRUCTURED,
                    json={
                        "system_type": system_type,
                        "functional_requirements": functional_requirements,
                        "non_functional_requirements": non_functional_requirements,
                        "architecture_preference": architecture_preference
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.recommendations = result.get("response", "No recommendation received.")
                    st.session_state.conversation_id = result.get("conversation_id")
                    ai_response = {
                        "text": "🤖 " + st.session_state.recommendations,
                        "images": result.get("images", []),
                        "sources": result.get("sources", [])
                    }
                    st.session_state.chat_history.append(("🧑‍💻 My system details", ai_response))
                    st.session_state.stage = "chat"
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

# Step 2: Chat + ADR
if st.session_state.stage == "chat":
    st.subheader("💬 Chat with the AI Architect")

    for user_msg, ai_msg in st.session_state.chat_history:
        st.markdown(f"**{user_msg}**")
        st.markdown(ai_msg.get("text", ""))
        if ai_msg.get("images"):
            for img_path in ai_msg["images"]:
                try:
                    img = Image.open(img_path)
                    img = img.resize((500, 400))
                    st.image(img)
                except Exception as e:
                    st.warning(f"Failed to load image: {img_path}\nError: {e}")
        if ai_msg.get("sources"):
            st.markdown("**Sources:**")
            for source in ai_msg["sources"]:
                st.markdown(f"- {source}")
        st.markdown("---")

    user_query = st.text_input("Ask me anything about your architecture:", key="chat_input")

    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        if st.button("Ask AI") and user_query.strip():
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        BACKEND_URL_OPEN_ENDED,
                        json={
                            "query": user_query,
                            "conversation_id": st.session_state.conversation_id
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        images = result.get("images", [])
                        ai_response = {
                            "text": "🤖 " + result.get("response", "No response received."),
                            "images": images,
                            "sources": result.get("sources", [])
                        }
                        st.session_state.chat_history.append(("🧑‍💻 " + user_query, ai_response))
                        st.session_state.generated_images = images
                        st.session_state.clear_input = True
                        st.rerun()
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Connection error: {e}")

    with col2:
        if st.button("Restart Conversation"):
            st.session_state.clear()
            st.session_state.stage = "questions"
            st.session_state.conversation_id = None
            st.rerun()

    with col3:
        if st.button("📝 Generate ADR"):
            with st.spinner("Generating ADR..."):
                try:
                    response = requests.post(
                        BACKEND_URL_ADR,
                        json={
                            "system_type": st.session_state.get("system_type", ""),
                            "functional_requirements": st.session_state.get("functional_requirements", ""),
                            "non_functional_requirements": st.session_state.get("non_functional_requirements", ""),
                            "architecture_preference": st.session_state.get("architecture_preference", ""),
                            "conversation_id": st.session_state.get("conversation_id", ""),
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        adr_text = result.get("adr", "")
                        st.session_state.adr_text = adr_text
                        images = result.get("images", [])
                        st.session_state.generated_images = images

                        adr_pdf = generate_adr_pdf(adr_text=adr_text, images=images)
                        adr_bytes = BytesIO()
                        adr_pdf.output(adr_bytes)
                        adr_bytes.seek(0)
                        st.session_state.adr_pdf_bytes = adr_bytes
                        st.success("✅ ADR ready to download below!")

                        st.rerun()
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Connection error: {e}")

    # ADR download button appears automatically after generation
    if st.session_state.get("adr_pdf_bytes"):
        st.download_button(
            label="📄 Click to download your ADR",
            data=st.session_state.adr_pdf_bytes,
            file_name=f"ADR_{st.session_state.conversation_id or 'session'}.pdf",
            mime="application/pdf"
        )
