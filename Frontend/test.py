import streamlit as st
import requests
from fpdf import FPDF
from io import BytesIO
from PIL import Image
from config import FUNCTIONAL_REQUIREMENTS, NON_FUNCTIONAL_REQUIREMENTS
from utils import generate_adr_pdf
from streamlit_custom_notification_box import custom_notification_box

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

# Clear input if flag set
if st.session_state.clear_input:
    st.session_state.chat_input = ""
    st.session_state.clear_input = False

# Step 1: Questions
if st.session_state.stage == "questions":
    st.subheader("Step 1: Tell me about your project")

    system_type = st.selectbox(
        "What type of system are you designing?",
        ["Real-time analytics", "E-commerce platform", "IoT system", "Other"]
    )

    functional_requirements = st.multiselect("Select your functional requirements", FUNCTIONAL_REQUIREMENTS)

    custom_func_input = st.text_input(
        "Add custom functional requirements (comma separated), leave empty if none:",
        key="custom_func_input"
    )

    if custom_func_input:
        new_reqs = [req.strip() for req in custom_func_input.split(",") if req.strip()]
        st.session_state.custom_func_reqs = list(dict.fromkeys(st.session_state.custom_func_reqs + new_reqs))

    non_functional_requirements = st.multiselect("Select your non functional requirements", NON_FUNCTIONAL_REQUIREMENTS)

    custom_non_func_input = st.text_input(
        "Add custom non-functional requirements (comma separated), leave empty if none:",
        key="custom_non_func_input"
    )

    if custom_non_func_input:
        new_non_reqs = [req.strip() for req in custom_non_func_input.split(",") if req.strip()]
        st.session_state.custom_non_func_reqs = list(dict.fromkeys(st.session_state.custom_non_func_reqs + new_non_reqs))

    all_functional_requirements = list(dict.fromkeys(functional_requirements + st.session_state.custom_func_reqs))
    all_non_functional_requirements = list(dict.fromkeys(non_functional_requirements + st.session_state.custom_non_func_reqs))

    architecture_preference = st.radio(
        "Do you prefer a specific architecture pattern?",
        ["Microservices", "Monolithic", "Event-Driven", "Not sure"]
    )

    if st.button("Get Recommendations"):
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
                        "text": "🤖 " + str(st.session_state.recommendations),
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

    # Display chat history
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

    # If there's a filtered query response, display it at the end (but don't append to history)
    if "temp_query" in st.session_state and "temp_response" in st.session_state:
        st.markdown(f"**🧑‍💻 {st.session_state.temp_query}**")
        st.markdown(st.session_state.temp_response.get("text", ""))
        if st.session_state.temp_response.get("images"):
            for img_path in st.session_state.temp_response["images"]:
                try:
                    img = Image.open(img_path)
                    img = img.resize((500, 400))
                    st.image(img)
                except Exception as e:
                    st.warning(f"Failed to load image: {img_path}\nError: {e}")
        if st.session_state.temp_response.get("sources"):
            st.markdown("**Sources:**")
            for source in st.session_state.temp_response["sources"]:
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
                        response_text = result.get("response", "No response received.")

                        ai_response = {
                            "text": "🤖 " + response_text,
                            "images": images,
                            "sources": result.get("sources", [])
                        }

                        st.session_state.generated_images = images
                        st.session_state.clear_input = True

                        if not result.get("filtered", False):
                            st.session_state.chat_history.append(("🧑‍💻 " + user_query, ai_response))
                            if "temp_query" in st.session_state:
                                del st.session_state.temp_query
                            if "temp_response" in st.session_state:
                                del st.session_state.temp_response
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





import argparse
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
from typing import List, Dict, Optional, Tuple

BASE_PDF_URL = "http://localhost:8000/files/"

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are an AI Software Architecture Assistant. Use the following context and conversation history to answer the question.

Context:
{context}

---

Conversation History:
{history}

---

Current Question: {question}

Provide a detailed, professional response focusing on software architecture best practices.
Include relevant examples when appropriate.
"""

def is_architecture_related(query: str) -> bool:
    architecture_keywords = [
        "architecture", "design pattern", "microservices", "monolith", "event-driven",
        "scalability", "availability", "fault tolerance", "deployment", "API gateway",
        "container", "CI/CD", "load balancing", "domain-driven design", "soa",
        "component", "distributed", "infrastructure", "cloud-native", "system design"
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in architecture_keywords)

def filter_duplicate_sources(
    results: List[Tuple[object, float]]
) -> Tuple[List[Tuple[object, float]], List[Tuple[object, float]]]:
    """
    Filters out duplicate documents based on the 'source' metadata field.

    Returns a tuple of (unique_results, duplicates)
    """
    seen_sources = set()
    unique_results = []
    duplicates = []

    for doc, score in results:
        source = doc.metadata.get("source")
        if source is None:
            # No source metadata, treat as unique
            unique_results.append((doc, score))
        elif source not in seen_sources:
            seen_sources.add(source)
            unique_results.append((doc, score))
        else:
            duplicates.append((doc, score))

    return unique_results, duplicates

def query_rag(query_text: str, conversation_history: Optional[List[Dict]] = None):
    if conversation_history is None:
        conversation_history = []
    # Filter unrelated queries
    if not is_architecture_related(query_text):
        return {
            "response": (
                "❌ This assistant is focused on **Software Architecture Design**. "
                "Please ask questions related to system architecture, design patterns, or related decisions."
            ),
            "images": [],
            "sources": [],
            "filtered": True
        }
    # Prepare the DB
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    
    # Search the DB
    results = db.similarity_search_with_score(query_text, k=5)

    # Filter duplicates by source
    results, duplicates = filter_duplicate_sources(results)

    if not results:
        return {
            "response": "No relevant architectural documents found. Could you provide more details about your system?",
            "images": [],
            "sources": []
        }
    
    # Format context and history
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    history_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" 
        for msg in conversation_history[-6:]  # Keep last 6 messages
    ) if conversation_history else "No previous conversation"
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt_str = str(prompt_template.format(
        context=context_text,
        history=history_text,
        question=query_text
    ))
    
    # Configure the remote Ollama instance
    model = Ollama(
        model="llama3.2:latest",
        base_url="http://86.50.169.115:11434",  
        temperature=0.7,
        top_p=0.9,
        timeout=60  
    )
    
    try:
        response_text = model.invoke(prompt_str)
    except Exception as e:
        return {
            "response": f"Error connecting to the AI model: {str(e)}",
            "images": [],
            "sources": []
        }

    # Process sources from unique results
    formatted_sources = []
    for i, (doc, score) in enumerate(results, 1):
        metadata = doc.metadata or {}
        source = metadata.get("source", metadata.get("id", "Unknown"))
        formatted_sources.append(f"Source {i}: Source: {source}")


    # Search for images
    matched_images = search_images(query_text, similarity_threshold=0.89, top_k=2)
    
    return {
        "response": response_text,
        "images": matched_images,
        "sources": formatted_sources
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    result = query_rag(query_text)
    print(result)  # or handle the result as needed

if __name__ == "__main__":
    main()



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from query_data import query_rag
import os

app = FastAPI()

# Allow all CORS for development (you can restrict this later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Use the correct relative path to serve PDFs
pdf_dir = os.path.abspath("data")
print("✅ Serving PDF directory from:", pdf_dir)

# Ensure the folder exists
if not os.path.exists(pdf_dir):
    raise RuntimeError(f"❌ Directory not found: {pdf_dir}")

# Serve static PDF files at /files/*
app.mount("/files", StaticFiles(directory=pdf_dir), name="files")

# Test endpoint
@app.get("/ping")
def ping():
    return {"message": "pong"}

# Request models
class StructuredQuery(BaseModel):
    system_type: str
    functional_requirements: list
    non_functional_requirements: list
    architecture_preference: str

class OpenEndedQuery(BaseModel):
    query: str

# Endpoint for structured input
@app.post("/structured-query")
def handle_structured_query(data: StructuredQuery):
    full_query = (
        f"System Type: {data.system_type}\n"
        f"Functional Requirements: {', '.join(data.functional_requirements)}\n"
        f"Non-Functional Requirements: {', '.join(data.non_functional_requirements)}\n"
        f"Preferred Architecture: {data.architecture_preference}\n\n"
        f"What is the best approach?"
    )
    response_text = query_rag(full_query)
    return {"response": response_text}

# Endpoint for open-ended query
@app.post("/query")
def handle_open_ended_query(data: OpenEndedQuery):
    response_text = query_rag(data.query)
    return {"response": response_text}
