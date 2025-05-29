import streamlit as st
import requests
from fpdf import FPDF
import re
from io import BytesIO
from PIL import Image
from utils import generate_adr_pdf
from streamlit_custom_notification_box import custom_notification_box
from config import FUNCTIONAL_REQUIREMENTS, NON_FUNCTIONAL_REQUIREMENTS
import streamlit_tags as st_tags
# Backend endpoints
BACKEND_URL_STRUCTURED = "http://127.0.0.1:8000/structured-query"
BACKEND_URL_OPEN_ENDED = "http://127.0.0.1:8000/query"
BACKEND_URL_ADR = "http://127.0.0.1:8000/generate-adr"

# Page config
st.set_page_config(page_title="AI Software Architect", layout="wide")
st.title("🧠 AI-Powered Software Architecture Assistant")

styles = {'material-icons':{'color': 'red'},
          'text-icon-link-close-container': {'box-shadow': '#3896de 0px 4px'},
          'notification-text': {'':''},
          'close-button':{'':''},
          'link':{'':''}}

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
if "custom_func_reqs" not in st.session_state:
    st.session_state.custom_func_reqs = []
if "custom_non_func_reqs" not in st.session_state:
    st.session_state.custom_non_func_reqs = []
if "func_reqs" not in st.session_state:
    st.session_state.func_reqs = []
if "non_func_reqs" not in st.session_state:
    st.session_state.non_func_reqs = []
    
    
# Clear input if flag set
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False


# Step 1: Questions
# Step 1: Questions
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    system_type = st.selectbox(
        "What type of system are you designing?",
        ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
    )

    func_reqs = st.multiselect("Select your functional requirements", FUNCTIONAL_REQUIREMENTS, key="func_reqs")

    custom_func_reqs = st_tags.st_tags(
        label="Add custom functional requirements (tags):",
        text="Press enter to add",
        value=st.session_state.get("custom_func_reqs", []),
        key="custom_func_tags"
    )
    st.session_state.custom_func_reqs = custom_func_reqs

    non_func_reqs = st.multiselect("Select your non functional requirements", NON_FUNCTIONAL_REQUIREMENTS, key="non_func_reqs")

    custom_non_func_reqs = st_tags.st_tags(
        label="Add custom non-functional requirements (tags):",
        text="Press enter to add",
        value=st.session_state.get("custom_non_func_reqs", []),
        key="custom_non_func_tags"
    )
    st.session_state.custom_non_func_reqs = custom_non_func_reqs
    all_functional_requirements = list(dict.fromkeys(func_reqs + st.session_state.custom_func_reqs))
    all_non_functional_requirements = list(dict.fromkeys(non_func_reqs + st.session_state.custom_non_func_reqs))

    architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"]
    )
    
    
    if st.button("Get Recommendations"):
        if not all_functional_requirements:
            st.warning("Please select at least one functional requirement or add a custom one.")
        elif not all_non_functional_requirements:
            st.warning("Please select at least one non-functional requirement or add a custom one.")
        else:
            with st.spinner("Generating recommendation..."):
                try:
                    st.session_state.system_type = system_type
                    st.session_state.functional_requirements = all_functional_requirements
                    st.session_state.non_functional_requirements = all_non_functional_requirements
                    st.session_state.architecture_preference = architecture_preference
                    response = requests.post(
                        BACKEND_URL_STRUCTURED,
                        json={
                            "system_type": system_type,
                            "functional_requirements": all_functional_requirements,
                            "non_functional_requirements": all_non_functional_requirements,
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
                st.markdown(source, unsafe_allow_html=True)

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
            keys_to_reset = list(st.session_state.keys())
            for key in keys_to_reset:
                del st.session_state[key]
            st.session_state.setdefault("func_reqs", [])
            st.session_state.stage = "questions"
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
