import streamlit as st
import requests
from fpdf import FPDF
import html
import re
from io import BytesIO

# FastAPI Backend URLs
BACKEND_URL_STRUCTURED = "http://127.0.0.1:8000/structured-query"
BACKEND_URL_OPEN_ENDED = "http://127.0.0.1:8000/query"

# Set Streamlit page configuration
st.set_page_config(page_title="AI Software Architect", layout="wide")
st.title("🧠 AI-Powered Software Architecture Assistant")

# Initialize session state
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

# Clear input safely before rendering input widget
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False

def clean_text(text):
    """Remove unwanted characters and format text for PDF"""

    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  
    text = re.sub(r'_(.*?)_', r'\1', text)       
    text = re.sub(r'`(.*?)`', r'\1', text)       
    text = re.sub(r'#+\s*', '', text)            
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)   
  
    emoji_map = {
        "🧠": "[AI]",
        "🧑‍💻": "[User]",
        "🤖": "[AI]",
        "❌": "[Error]",
        "⚠️": "[Warning]"
    }
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
 
    text = html.unescape(text)
    return text.strip()

def generate_pdf(chat_history):
    """Generate PDF from chat history"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="AI-Powered Software Architecture Assistant", ln=1, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    if st.session_state.conversation_id:
        pdf.cell(200, 10, txt=f"Conversation ID: {st.session_state.conversation_id}", ln=1)
        pdf.ln(5)
    
    for user_msg, ai_msg in chat_history:
        user_msg_clean = clean_text(user_msg)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=user_msg_clean, ln=1)
        
        ai_msg_clean = clean_text(ai_msg)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=ai_msg_clean)
        pdf.ln(5)
    
    return pdf

# Step 1: Guided Questions
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    system_type = st.selectbox(
        "What type of system are you designing?",
        ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
    )

    key_requirements = st.multiselect(
        "Select your key requirements",
        ["Scalability", "Low Latency", "Security", "High Availability", "Fault Tolerance"]
    )

    architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"]
    )

    if st.button("Get Recommendations"):
        with st.spinner("Generating recommendation..."):
            try:
                response = requests.post(
                    BACKEND_URL_STRUCTURED,
                    json={
                        "system_type": system_type,
                        "key_requirements": key_requirements,
                        "architecture_preference": architecture_preference
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.recommendations = result.get("response", "No recommendation received.")
                    st.session_state.conversation_id = result.get("conversation_id")
                    st.session_state.stage = "chat"
                    st.session_state.chat_history.append(("🧑‍💻 My system details", "🤖 " + st.session_state.recommendations))
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

# Step 2: Chat Mode
if st.session_state.stage == "chat":
    st.subheader("💬 Chat with the AI Architect")

    for user_msg, ai_msg in st.session_state.chat_history:
        st.markdown(f"**{user_msg}**")
        st.markdown(f"{ai_msg}")
        st.markdown("---")

    user_query = st.text_input(
        "Ask me anything about your architecture:",
        key="chat_input"
    )

    col1, col2 = st.columns([1, 6])
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
                        ai_response = result.get("response", "No response received.")
                        st.session_state.chat_history.append(("🧑‍💻 " + user_query, "🤖 " + ai_response))
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

    if st.session_state.chat_history:
        pdf = generate_pdf(st.session_state.chat_history)
        pdf_bytes = BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)
        
        st.download_button(
            label="Export to PDF",
            data=pdf_bytes,
            file_name=f"architecture_chat_{st.session_state.conversation_id or 'session'}.pdf",
            mime="application/pdf",
            key="pdf_download"
        )
    else:
        st.warning("No chat history to export")