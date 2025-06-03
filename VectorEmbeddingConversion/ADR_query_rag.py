from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
from typing import Dict, List, Optional
import re
from datetime import date


CHROMA_PATH = "chroma"

# Prompt now fully delegates UML generation to the LLM

ADR_GENERATION_TEMPLATE = """
You are a software architect documenting architectural decisions for future reference.

Generate an Architectural Decision Record (ADR) using the following input. Follow this format:

Title: [Decision title]

**ADR Number**: {adr_id}  
**Status**: Accepted  
**Date**: {dateAdded}  
**Deciders**: {deciders}  
**Superseded by**: [Optional]

---

### Context
{context}

### Decision  
[Describe the architectural decision taken based on the context.]

### Consequences  
[Explain the consequences, both positive and negative, of the decision.]

### Alternatives Considered  
[List and briefly describe the alternative approaches that were considered.]

---

Use markdown formatting. You must fill in the **Decision**, **Consequences**, and **Alternatives Considered** sections clearly.
"""


def get_current_date() -> str:
    return date.today().isoformat()  # Returns '2025-06-02'

def extract_all_plantuml(markdown_text: str) -> List[str]:
    """
    Extract all PlantUML code blocks from the markdown text.
    Returns a list of PlantUML source code strings.
    """
    pattern = r"```plantuml\s*(.*?)```"
    matches = re.findall(pattern, markdown_text, re.DOTALL)
    # Strip whitespace from each matched code block
    return [match.strip() for match in matches]

def generate_architecture_report(
    system_type: str,
    functional_requirements: str,
    non_functional_requirements: str,
    architecture_preference: str,
    adr_id: int,
    deciders: str = "Architecture Team",
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, str]:
    # Initialize vector database for related content
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    search_query = f"{system_type} {functional_requirements} {non_functional_requirements}"
    results = db.similarity_search_with_score(search_query, k=5)

    # Optional image results
    architecture_preference = architecture_preference + " Architecture"
    print(architecture_preference)
    matched_images = search_images(architecture_preference, similarity_threshold=0.85, top_k=2)
    print(matched_images)
    # Prepare conversation context (if provided)
    formatted_conversation = ""
    if conversation_history:
        formatted_conversation = "\n".join(
            f"**{msg.get('role', 'user').capitalize()}**: {msg.get('content', '')}"
            for msg in conversation_history
        )
    # Fill prompt template
    prompt = ChatPromptTemplate.from_template(ADR_GENERATION_TEMPLATE)
    prompt_str = prompt.format(
    adr_id=adr_id,
    dateAdded=get_current_date(),
    deciders=deciders,
    context=f"""
**System Type**: {system_type}

**Functional Requirements**:  
{functional_requirements}

**Non-Functional Requirements**:  
{non_functional_requirements}

**Architecture Preference**:  
{architecture_preference}

**Prior Discussion**:  
{formatted_conversation if formatted_conversation else 'N/A'}
"""
)

    # Initialize the LLM
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
            "report": f"Error generating report: {str(e)}",
            "images": [],
            "sources": []
        }

    # Format document source references
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

