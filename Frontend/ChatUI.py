import streamlit as st
import requests

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

# Clear input safely before rendering input widget
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False

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
                    st.session_state.stage = "chat"
                    st.session_state.chat_history.append(("🧑‍💻 My system details", "🤖 " + st.session_state.recommendations))
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

# Step 2: Chat Mode
if st.session_state.stage == "chat":
    st.subheader("💬 Chat with the AI Architect")

    # Display chat history
    for user_msg, ai_msg in st.session_state.chat_history:
        st.markdown(f"**{user_msg}**")
        st.markdown(f"{ai_msg}")
        st.markdown("---")

    # Input for chat
    user_query = st.text_input(
        "Ask me anything about your architecture:",
        key="chat_input"
    )

    if st.button("Ask AI") and user_query.strip():
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    BACKEND_URL_OPEN_ENDED,
                    json={"query": user_query}
                )
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "No response received.")
                    st.session_state.chat_history.append(("🧑‍💻 " + user_query, "🤖 " + ai_response))
                    st.session_state.clear_input = True  # safely clear input next cycle
                    st.rerun()
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

    if st.button("Restart"):
        st.session_state.clear()
        st.rerun()
