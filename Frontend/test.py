import streamlit as st
import requests
from fpdf import FPDF
from io import BytesIO
from PIL import Image
from config import FUNCTIONAL_REQUIREMENTS, NON_FUNCTIONAL_REQUIREMENTS
from utils import generate_adr_pdf
from streamlit_custom_notification_box import custom_notification_box
import streamlit_tags as st_tags

# Backend endpoints
BACKEND_URL_STRUCTURED = "http://127.0.0.1:8000/structured-query"
BACKEND_URL_OPEN_ENDED = "http://127.0.0.1:8000/query"
BACKEND_URL_ADR = "http://127.0.0.1:8000/generate-adr"
PDF_BASE_URL = "http://127.0.0.1:8000/files/"

# Page config
st.set_page_config(page_title="AI Software Architect", layout="wide")
st.title("🧠 AI-Powered Software Architecture Assistant")

# Initialize session state defaults
DEFAULT_SESSION = {
    "stage": "questions",
    "recommendations": "",
    "chat_history": [],
    "chat_input": "",
    "clear_input": False,
    "conversation_id": None,
    "adr_text": "",
    "adr_pdf_bytes": None,
    "custom_func_reqs": [],
    "custom_non_func_reqs": []
}
for k, v in DEFAULT_SESSION.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False

# ---------------------- Step 1: Questions ----------------------
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    system_type = st.selectbox(
        "What type of system are you designing?",
        ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
    )

    functional_requirements = st.multiselect("Select your functional requirements", FUNCTIONAL_REQUIREMENTS)
    custom_func_reqs = st_tags.st_tags(
        label="Add custom functional requirements (tags):",
        text="Press enter to add",
        value=st.session_state.get("custom_func_reqs", []),
        key="custom_func_tags"
    )
    st.session_state.custom_func_reqs = custom_func_reqs

    non_functional_requirements = st.multiselect("Select your non functional requirements", NON_FUNCTIONAL_REQUIREMENTS)
    custom_non_func_reqs = st_tags.st_tags(
        label="Add custom non-functional requirements (tags):",
        text="Press enter to add",
        value=st.session_state.get("custom_non_func_reqs", []),
        key="custom_non_func_tags"
    )
    st.session_state.custom_non_func_reqs = custom_non_func_reqs

    all_functional_requirements = list(dict.fromkeys(functional_requirements + st.session_state.custom_func_reqs))
    all_non_functional_requirements = list(dict.fromkeys(non_functional_requirements + st.session_state.custom_non_func_reqs))

    architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"]
    )

    if st.button("Get Recommendations"):
        if not system_type or not all_functional_requirements or not all_non_functional_requirements or not architecture_preference:
            st.warning("⚠️ Please complete all fields before continuing.")
        else:
            with st.spinner("Generating recommendation..."):
                try:
                    response = requests.post(BACKEND_URL_STRUCTURED, json={
                        "system_type": system_type,
                        "functional_requirements": all_functional_requirements,
                        "non_functional_requirements": all_non_functional_requirements,
                        "architecture_preference": architecture_preference
                    })
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.recommendations = result.get("response", "No recommendation received.")
                        st.session_state.conversation_id = result.get("conversation_id")
                        ai_response = {
                            "text": "🤖 " + st.session_state.get("recommendations", ""),
                            "images": result.get("images", []),
                            "sources": result.get("sources", [])
                        }
                        st.session_state.chat_history.append(("🧑‍💻 My system details", ai_response))
                        st.session_state.stage = "chat"
                        st.rerun()
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Connection error: {e}")

# ---------------------- Step 2: Chat + ADR ----------------------
elif st.session_state.stage == "chat":
    st.subheader("💬 Chat with the AI Architect")

    def render_sources(sources):
        for source in sources:
            if source.endswith(".pdf"):
                st.markdown(f"[📄 View PDF]({PDF_BASE_URL}{source})", unsafe_allow_html=True)
            else:
                st.markdown(source, unsafe_allow_html=True)

    for user_msg, ai_msg in st.session_state.chat_history:
        st.markdown(f"**{user_msg}**")
        st.markdown(ai_msg.get("text", ""))
        if ai_msg.get("images"):
            for img_path in ai_msg["images"]:
                try:
                    st.image(Image.open(img_path).resize((500, 400)))
                except Exception as e:
                    st.warning(f"Failed to load image: {img_path}\nError: {e}")
        if ai_msg.get("sources"):
            st.markdown("**Sources:**")
            render_sources(ai_msg["sources"])
        st.markdown("---")

    if "temp_query" in st.session_state and "temp_response" in st.session_state:
        st.markdown(f"**🧑‍💻 {st.session_state.temp_query}**")
        st.markdown(st.session_state.temp_response.get("text", ""))
        if st.session_state.temp_response.get("images"):
            for img_path in st.session_state.temp_response["images"]:
                try:
                    st.image(Image.open(img_path).resize((500, 400)))
                except Exception as e:
                    st.warning(f"Failed to load image: {img_path}\nError: {e}")
        if st.session_state.temp_response.get("sources"):
            st.markdown("**Sources:**")
            render_sources(st.session_state.temp_response["sources"])
        st.markdown("---")

    user_query = st.text_input("Ask me anything about your architecture:", key="chat_input")
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        if st.button("Ask AI") and user_query.strip():
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(BACKEND_URL_OPEN_ENDED, json={
                        "query": user_query,
                        "conversation_id": st.session_state.get("conversation_id")
                    })
                    if response.status_code == 200:
                        result = response.json()
                        ai_response = {
                            "text": "🤖 " + result.get("response", "No response received."),
                            "images": result.get("images", []),
                            "sources": result.get("sources", [])
                        }
                        if not result.get("filtered", False):
                            st.session_state.chat_history.append(("🧑‍💻 " + user_query, ai_response))
                            st.session_state.clear_input = True
                            st.session_state.pop("temp_query", None)
                            st.session_state.pop("temp_response", None)
                        else:
                            st.session_state.temp_query = user_query
                            st.session_state.temp_response = ai_response
                        st.rerun()
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Connection error: {e}")

    with col2:
        if st.button("Restart Conversation"):
            st.session_state.clear()
            for k, v in DEFAULT_SESSION.items():
                st.session_state[k] = v
            st.rerun()

    with col3:
        if st.button("📝 Generate ADR"):
            with st.spinner("Generating ADR..."):
                try:
                    response = requests.post(BACKEND_URL_ADR, json={
                        "system_type": st.session_state.get("system_type", ""),
                        "functional_requirements": st.session_state.get("functional_requirements", []),
                        "non_functional_requirements": st.session_state.get("non_functional_requirements", []),
                        "architecture_preference": st.session_state.get("architecture_preference", ""),
                        "conversation_id": st.session_state.get("conversation_id", "")
                    })
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.adr_text = result.get("adr", "")
                        st.session_state.generated_images = result.get("images", [])
                        adr_pdf = generate_adr_pdf(
                            adr_text=st.session_state.adr_text,
                            images=st.session_state.generated_images
                        )
                        adr_bytes = BytesIO()
                        adr_pdf.output(adr_bytes, 'F')
                        adr_bytes.seek(0)
                        st.session_state.adr_pdf_bytes = adr_bytes
                        st.success("✅ ADR ready to download below!")
                        st.rerun()
                    else:
                        st.error(f"❌ Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Connection error: {e}")

    if st.session_state.get("adr_pdf_bytes"):
        st.download_button(
            label="📄 Click to download your ADR",
            data=st.session_state.adr_pdf_bytes,
            file_name=f"ADR_{st.session_state.conversation_id or 'session'}.pdf",
            mime="application/pdf"
        )
