import streamlit as st
import requests
from io import BytesIO
from PIL import Image
from utils import generate_adr_pdf, generate_chat_pdf
from config import FUNCTIONAL_REQUIREMENTS, NON_FUNCTIONAL_REQUIREMENTS
import streamlit_tags as st_tags

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
if "custom_func_reqs" not in st.session_state:
    st.session_state.custom_func_reqs = []
if "custom_non_func_reqs" not in st.session_state:
    st.session_state.custom_non_func_reqs = []
if "func_reqs" not in st.session_state:
    st.session_state.func_reqs = []
if "non_func_reqs" not in st.session_state:
    st.session_state.non_func_reqs = []
if "project_description" not in st.session_state:
    st.session_state.project_description = None
        
    
# Clear input if flag set
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False


# Step 1: Questions
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    col1, col2 = st.columns(2)

    # Row 1
    with col1:
        system_type = st.selectbox(
            "What type of system are you designing?",
            ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
        )
    with col2:
        architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"], horizontal=True
    )

    # Row 2
    with col1:
        func_reqs = st.multiselect("Select your functional requirements", FUNCTIONAL_REQUIREMENTS, key="func_reqs")
    with col2:
        non_func_reqs = st.multiselect("Select your non functional requirements", NON_FUNCTIONAL_REQUIREMENTS, key="non_func_reqs")

    # Row 3
    with col1:
        custom_func_reqs = st_tags.st_tags(
            label="Add custom functional requirements (tags):",
            text="Press enter to add",
            value=st.session_state.get("custom_func_reqs", []),
            key="custom_func_tags"
        )
        st.session_state.custom_func_reqs = custom_func_reqs

    with col2:
        custom_non_func_reqs = st_tags.st_tags(
            label="Add custom non-functional requirements (tags):",
            text="Press enter to add",
            value=st.session_state.get("custom_non_func_reqs", []),
            key="custom_non_func_tags"
        )
        st.session_state.custom_non_func_reqs = custom_non_func_reqs

    # Combine selected + custom requirements
    all_functional_requirements = list(dict.fromkeys(func_reqs + st.session_state.custom_func_reqs))
    all_non_functional_requirements = list(dict.fromkeys(non_func_reqs + st.session_state.custom_non_func_reqs))
    
    # Project description - full width
    project_description = st.text_area(
        "Describe your project in a few sentences:",
        value=st.session_state.get("project_description", ""),
        height=100
    )
    st.session_state.project_description = project_description

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
                    st.session_state. project_description = project_description
                    response = requests.post(
                        BACKEND_URL_STRUCTURED,
                        json={
                            "system_type": system_type,
                            "functional_requirements": all_functional_requirements,
                            "non_functional_requirements": all_non_functional_requirements,
                            "architecture_preference": architecture_preference,
                            "project_description": project_description
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.recommendations = result.get("response", "No recommendation received.")
                        st.session_state.conversation_id = result.get("conversation_id")
                        if result.get("original_preference_unspecified"):
                            print(result.get("generated_architecture_preference", "No preference"))
                            st.session_state.architecture_preference = result.get("generated_architecture_preference", "No preference")  + " architecture"
                        ai_response = {
                            "text": "🤖 " + st.session_state.recommendations,
                            "images": result.get("images", []),
                            "sources": result.get("sources", [])
                        }
                        print( result.get("sources", []))
                        st.session_state.chat_history.append(("🧑‍💻 My system details", ai_response))
                        st.session_state.stage = "chat"
                        st.rerun()
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
            st.markdown("*These are example images for the suggested architecture:*")
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
    if "temp_query" in st.session_state and "temp_response" in st.session_state:
        st.markdown(f"**🧑‍💻 {st.session_state.temp_query}**")
        st.markdown(st.session_state.temp_response.get("text", ""))
        if st.session_state.temp_response.get("images"):
            for img_path in st.session_state.temp_response["images"]:
                try:
                    st.image(Image.open(img_path).resize((500, 400)))
                except Exception as e:
                    st.warning(f"Failed to load image: {img_path}\nError: {e}")
        st.markdown("---")

    user_query = st.text_input("Ask me anything about your architecture:", key="chat_input")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.button("Ask AI") and user_query.strip():
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(BACKEND_URL_OPEN_ENDED, json={
                        "query": user_query,
                        "conversation_id": st.session_state.get("conversation_id"),
                         "system_type": st.session_state.system_type,
                        "functional_requirements":  st.session_state.functional_requirements,
                        "non_functional_requirements":  st.session_state.non_functional_requirements,
                        "architecture_preference": st.session_state.architecture_preference,
                        "project_description": st.session_state. project_description
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
        with st.container():
            if st.button("🗂️ Export Chat as PDF"):
                if st.session_state.chat_history:
                    chat_pdf = generate_chat_pdf(st.session_state.chat_history)
                    chat_bytes = BytesIO()
                    chat_pdf.output(chat_bytes)
                    chat_bytes.seek(0)
                    st.download_button(
                        label="📥 Download Chat History PDF",
                        data=chat_bytes,
                        file_name=f"Chat_History_{st.session_state.conversation_id or 'session'}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("Chat history is empty.")
    with col3:
        if st.button("Restart Conversation"):
            keys_to_reset = list(st.session_state.keys())
            for key in keys_to_reset:
                del st.session_state[key]
            st.session_state.setdefault("func_reqs", [])
            st.session_state.stage = "questions"
            st.rerun()

    with col4:
        if st.button("📝 Generate ADR"):
            with st.spinner("Generating ADR..."):
                try:
                    arch_pref = st.session_state.get("architecture_preference", "")
                    # If it's a list, join it as a comma-separated string with no trailing comma
                    if isinstance(arch_pref, list):
                        arch_pref = ", ".join(map(str, arch_pref))
                        print(arch_pref)
                    response = requests.post(
                        BACKEND_URL_ADR,
                        json={
                            "system_type": st.session_state.get("system_type", ""),
                            "functional_requirements": st.session_state.get("functional_requirements", ""),
                            "non_functional_requirements": st.session_state.get("non_functional_requirements", ""),
                            "architecture_preference": arch_pref,
                            "project_description": st.session_state.get("project_description", ""),
                            "conversation_id": st.session_state.get("conversation_id")
                        }
                       
                    )
                    print( st.session_state.get("architecture_preference"))
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
