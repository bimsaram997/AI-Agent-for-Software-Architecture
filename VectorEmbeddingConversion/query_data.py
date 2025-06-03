import argparse
import re
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
You are an AI Software Architecture Assistant. Based on the provided system information, your goal is to recommend the most suitable software architecture for the project.

User Architecture Preference: {architecture_preference}

Instructions:
- If the user has given a specific architecture preference other than "No preference",
  you must recommend that architecture style.
- Do not recommend any other architecture unless the user preference is "No preference".
- If the preference is "No preference", recommend the best architecture based on the requirements.
- Always explain why the chosen architecture fits best.

---

System Type:
{system_type}

Functional Requirements:
{functional_requirements}

Non-Functional Requirements:
{non_functional_requirements}

Architecture Preferences (if any):
{architecture_preference}

Project Description:
{project_description}

---

Conversation History:
{history}

---

Your Response:
- Recommend the most appropriate architecture style (e.g., microservices, layered, event-driven, hexagonal, monolithic, etc.).
- Justify your recommendation based on system goals and trade-offs.
- Mention alternative architectures and why they are less suitable, if relevant.
- Include real-world examples or known use cases if possible.
- Include step by step process to build the system.
- Suggest suitable technologies(e.g., React, Docker, .Net Core)
- Be clear, structured, and professional.
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

def query_structured(
    query_text: str,
    system_type: str,
    functional_requirements: str,
    non_functional_requirements: str,
    architecture_preference: str,
    project_description:Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
                    )-> Dict[str, str]:
    if conversation_history is None:
        conversation_history = []
    
     # Normalize preference input
    original_preference_unspecified = False 
    if architecture_preference is None or architecture_preference.strip().lower() in ["", "not sure", "no preference", "none"]:
        architecture_preference = "No preference"
        original_preference_unspecified = True
    else:
    # Use exactly what user provided, e.g., "microservices", "layered"
        architecture_preference = architecture_preference.strip() + " Architecture"
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
    prompt_str = prompt_template.format(
        context=context_text,
        history=history_text,
        system_type=system_type,
        functional_requirements=functional_requirements,
        non_functional_requirements=non_functional_requirements,
        architecture_preference=architecture_preference,
        project_description=project_description
    )

    system_instruction = "Respect the user's architecture preference unless strong reasons justify a different recommendation."
    full_prompt = system_instruction + "\n\n" + prompt_str
    # Configure the remote Ollama instance
    model = Ollama(
        model="llama3.2:latest",
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.7,
        top_p=0.9,
        timeout=60  
    )
    
    try:
        response_text = model.invoke(full_prompt)
    except Exception as e:
        return {
            "response": f"Error connecting to the AI model: {str(e)}",
            "images": [],
            "sources": []
        }
     # Optionally extract a generated architecture suggestion if needed
    generated_architecture_preference = None
    if original_preference_unspecified:
        # Try to extract from the response (simple heuristic-based)
        match = re.search(r'(recommend(?:ed)?|suggest(?:ed)?|propose(?:d)?).{0,20}?(microservices|monolithic|layered|event[-\s]?driven|service[-\s]?oriented|client[-\s]?server|n[-\s]?tier|hexagonal)', response_text, re.IGNORECASE)
        if match:
            generated_architecture_preference = match.group(2).lower().replace('-', ' ').title() + " Architecture"
    
    # Process sources from unique results
    formatted_sources = []
    for i, (doc, score) in enumerate(results, 1):
        metadata = doc.metadata or {}
        source_path = metadata.get("source", metadata.get("id", "Unknown"))
        filename = os.path.basename(source_path)
        pdf_url = f"{PDF_BASE_URL}{filename}"
        formatted_sources.append(f'Source {i}: <a href="{pdf_url}" target="_blank">{filename}</a>')

    # Search for images
    matched_images = search_images(architecture_preference, similarity_threshold=0.89, top_k=2)
    
    return {
        "response": response_text,
        "images": matched_images,
        "sources": formatted_sources,
        "generated_architecture_preference": generated_architecture_preference ,
        "original_preference_unspecified": original_preference_unspecified
    }





def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    result = query_structured(query_text)

if __name__ == "__main__":
    main()
