import streamlit as st
import requests

# FastAPI Backend URLs
BACKEND_URL_STRUCTURED = "http://127.0.0.1:8000/structured-query"  # For structured input queries
BACKEND_URL_OPEN_ENDED = "http://127.0.0.1:8000/query"  # For open-ended queries

# Streamlit UI Setup
st.set_page_config(page_title="AI Software Architect", layout="wide")
st.title("🧠 AI-Powered Software Architecture Assistant")

# Track steps in session
if "stage" not in st.session_state:
    st.session_state.stage = "questions"

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

    # Structured Query Button
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
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

# Step 2: Chat Mode
if st.session_state.stage == "chat":
    st.subheader("💡 AI Recommendation")
    st.write(st.session_state.recommendations)

    st.subheader("💬 Open-Ended Chat")
    user_query = st.text_input("Ask me anything about your architecture:")

    # Open-ended Query Button
    if st.button("Ask AI") and user_query.strip():
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    BACKEND_URL_OPEN_ENDED,
                    json={"query": user_query}
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.last_response = result.get("response", "No response received.")
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Connection error: {e}")

    # Show last AI response
    if "last_response" in st.session_state:
        st.write("🤖 AI:", st.session_state.last_response)

    # Restart button to reset everything
    if st.button("Restart"):
        st.session_state.clear()
        st.rerun()