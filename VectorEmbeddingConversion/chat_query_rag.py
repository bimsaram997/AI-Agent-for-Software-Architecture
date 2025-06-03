import argparse
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
from typing import List, Dict, Optional, Tuple
import os
from dotenv import load_dotenv
load_dotenv()

PDF_BASE_URL = "http://127.0.0.1:8000/files/"
CHROMA_PATH = "chroma"
PROMPT_TEMPLATE = """
You are an AI Software Architecture Assistant helping with application design, architecture, and related best practices.

Use the following comprehensive context and conversation history to answer the user's current question professionally and accurately.

---

Full Query (system description, requirements, or previously recommended architecture):
{fullquery}

---

Supporting Context (retrieved content from related documents or architecture references):
{context}

---

Conversation History:
{history}

---

Current Question:
{question}

---

Guidelines for Response:
- Provide a clear, structured, and professional answer.
- Focus on **software architecture, design decisions, trade-offs, scalability, deployment, technology choices, and best practices**.
- Reference the full query or previous recommendations where relevant.
- Include real-world examples, comparisons, or analogies where helpful.
- Suggest technologies, tools, or patterns for implementation if appropriate.
- Avoid repeating earlier recommendations unless they are directly relevant.
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

def query_rag(fullquery: str, query_text: str, conversation_history: Optional[List[Dict]] = None):
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
        question=query_text,
        fullquery = fullquery
    ))
    
    # Configure the remote Ollama instance
    model = Ollama(
        model="llama3.2:latest",
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
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
        source_path = metadata.get("source", metadata.get("id", "Unknown"))
        filename = os.path.basename(source_path)
        pdf_url = f"{PDF_BASE_URL}{filename}"
        formatted_sources.append(f'Source {i}: <a href="{pdf_url}" target="_blank">{filename}</a>')

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

if __name__ == "__main__":
    main()
