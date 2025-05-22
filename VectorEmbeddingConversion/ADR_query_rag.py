from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
from typing import Dict

CHROMA_PATH = "chroma"

ARCHITECTURE_REPORT_TEMPLATE = """
You are an expert software architect.

Given the following project inputs, generate a structured software architecture report in markdown format with the following sections:

1. **System Overview** — including system type and a concise project summary.
2. **Functional Requirements** — list them clearly.
3. **Non-Functional Requirements** — list them clearly.
4. **Preferred Architecture Pattern** — include the pattern name and a rationale.
5. **Suggested Technologies** — recommend backend, frontend, database, and other key technologies.
6. **UML Diagrams** — placeholder for component and sequence diagrams.

User Inputs:
- System Type: {system_type}
- Functional Requirements: {functional_requirements}
- Non-Functional Requirements: {non_functional_requirements}
- Architecture Preference: {architecture_preference}

Use formal, professional language and output ONLY markdown content.
"""

def generate_architecture_report(
    system_type: str,
    functional_requirements: str,
    non_functional_requirements: str,
    architecture_preference: str
) -> Dict[str, str]:

    # Optionally pull context from vector DB
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    search_query = f"{system_type} {functional_requirements} {non_functional_requirements}"
    results = db.similarity_search_with_score(search_query, k=5)

    matched_images = search_images(architecture_preference, similarity_threshold=0.85, top_k=2)

    prompt = ChatPromptTemplate.from_template(ARCHITECTURE_REPORT_TEMPLATE)
    prompt_str = prompt.format(
        system_type=system_type,
        functional_requirements=functional_requirements,
        non_functional_requirements=non_functional_requirements,
        architecture_preference=architecture_preference
    )

    model = Ollama(
        model="llama3.2:latest",
        base_url="http://86.50.169.115:11434",
        temperature=0.6,
        top_p=0.9,
        timeout=60
    )

    try:
        markdown_report = model.invoke(prompt_str)
    except Exception as e:
        return {
            "report": f"Error generating report: {e}",
            "images": [],
            "sources": []
        }

    # Include formatted source metadata if needed
    formatted_sources = []
    for i, (doc, _) in enumerate(results, 1):
        meta = doc.metadata or {}
        formatted_sources.append(
            f"Source {i}: {meta.get('source', meta.get('id', 'Unknown'))}"
        )

    return {
        "report": markdown_report,
        "images": matched_images,
        "sources": formatted_sources
    }
