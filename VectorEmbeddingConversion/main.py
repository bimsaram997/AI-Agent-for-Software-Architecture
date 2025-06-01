from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_data import query_structured
from chat_query_rag import query_rag
from typing import Dict, List
import uuid
from ADR_query_rag import generate_architecture_report
import os
from fastapi.staticfiles import StaticFiles
from typing import Optional
import uuid

app = FastAPI()
pdf_dir = os.path.abspath("data")
print("✅ Serving PDF directory from:", pdf_dir)

# Ensure the folder exists
if not os.path.exists(pdf_dir):
    raise RuntimeError(f"❌ Directory not found: {pdf_dir}")

# Serve static PDF files at /files/*
app.mount("/files", StaticFiles(directory=pdf_dir), name="files")
conversation_db: Dict[str, List[Dict]] = {}



# Allow Streamlit access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class StructuredQuery(BaseModel):
    system_type: str
    functional_requirements: list
    non_functional_requirements:list
    architecture_preference: str
    project_description:Optional[str] = None

class OpenEndedQuery(BaseModel):
    query: str
    conversation_id: str = None
    system_type: str
    functional_requirements: list
    non_functional_requirements:list
    architecture_preference: str
    project_description:Optional[str] = None

class ADRQuery(BaseModel):
    system_type: str
    functional_requirements: list
    non_functional_requirements:list
    architecture_preference: str
    project_description: Optional[str] = None
    conversation_id: str = None

def generate_adr_id() -> str:
    return str(uuid.uuid4())
# Route: structured initial query
@app.post("/structured-query")
def handle_structured_query(data: StructuredQuery):
    full_query = f"""System Type: {data.system_type}
Functional Requirements: {', '.join(data.functional_requirements)}
Non-Functional Requirements: {', '.join(data.non_functional_requirements)}
Preferred Architecture: {data.architecture_preference}
Project Description: {data.project_description}
"""

    conv_id = str(uuid.uuid4())
    conversation_db[conv_id] = [{"role": "user", "content": full_query}]

    result = query_structured(
        full_query,
        system_type=data.system_type,
        functional_requirements=", ".join(data.functional_requirements),
        non_functional_requirements=", ".join(data.non_functional_requirements),
        architecture_preference=data.architecture_preference, 
        project_description=data.project_description,
        conversation_history=[])
    
    # Support both string and dict returns
    if isinstance(result, str):
        response_text = result
        images = []
        sources = []
        generated_architecture_preference = None
        original_preference_unspecified = False
    else:
        response_text = result.get("response", "")
        images = result.get("images", [])
        sources = result.get("sources", [])
        generated_architecture_preference= result.get("generated_architecture_preference", "")
        original_preference_unspecified =  result.get("original_preference_unspecified")

    conversation_db[conv_id].append({"role": "assistant", "content": response_text})

    return {
        "response": response_text,
        "images": images,
        "sources": sources,
        "conversation_id": conv_id,
        "generated_architecture_preference": generated_architecture_preference,
        "original_preference_unspecified": original_preference_unspecified
    }

# Route: follow-up chat queries
@app.post("/query")
def handle_open_ended_query(data: OpenEndedQuery):
    full_query = f"""System Type: {data.system_type}
    Functional Requirements: {', '.join(data.functional_requirements)}
    Non-Functional Requirements: {', '.join(data.non_functional_requirements)}
    Preferred Architecture: {data.architecture_preference}
    Project Description: {data.project_description}
    """
    conversation_history = []
    if data.conversation_id and data.conversation_id in conversation_db:
        conversation_history = conversation_db[data.conversation_id]

    # Append user query tentatively
    conversation_history.append({"role": "user", "content": data.query})

    # Run your RAG + query classifier here
    result = query_rag(full_query,
                       data.query,
                       conversation_history=conversation_history, )

    # If result is just string, make consistent dict
    if isinstance(result, str):
        response_text = result
        images = []
        sources = []
        filtered = False
    else:
        response_text = result.get("response", "")
        images = result.get("images", [])
        sources = result.get("sources", [])
        filtered = result.get("filtered", False)  # <-- expect this from query_rag

    # Append assistant response only if not filtered
    if not filtered:
        conversation_history.append({"role": "assistant", "content": response_text})
    else:
        # If filtered, remove the user query appended above to keep history clean
        conversation_history.pop()

    # Update conversation db only if not filtered
    if data.conversation_id and not filtered:
        conversation_db[data.conversation_id] = conversation_history

    # Return filtered flag for front-end use
    return {
        "response": response_text,
        "images": images,
        "sources": sources,
        "filtered": filtered
    }


# Route: ADR query
@app.post("/generate-adr")
def generate_adr(data: ADRQuery):
    conversation_history = []
    if data.conversation_id and data.conversation_id in conversation_db:
        conversation_history = conversation_db[data.conversation_id]
    print(data)
    
    adr_id = data.adr_id if hasattr(data, 'adr_id') and data.adr_id else generate_adr_id()
    user_input_summary = (
        f"System Type: {data.system_type}\n"
        f"Functional Requirements: {', '.join(data.functional_requirements)}\n"
        f"Non-Functional Requirements: {', '.join(data.non_functional_requirements)}\n"
        f"Architecture Preference: {data.architecture_preference}\n"
        f"Project Descripttion: {data.project_description}\n"
    )
    conversation_history.append({"role": "user", "content": user_input_summary})

    # Generate ADR markdown
    result = generate_architecture_report(
        system_type=data.system_type,
        functional_requirements=", ".join(data.functional_requirements),
        non_functional_requirements=", ".join(data.non_functional_requirements),
        architecture_preference=data.architecture_preference,
        adr_id=adr_id,
        conversation_history=conversation_history
    )

    adr_markdown = result.get("report", "No ADR content generated.")
    images = result.get("images", [])
    sources = result.get("sources", [])



    return {
        "conversation_id": data.conversation_id,
        "adr": adr_markdown,
        "images": images,
        "sources": sources
    }

    

# Optional: retrieve full history
@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    if conversation_id in conversation_db:
        return {"conversation": conversation_db[conversation_id]}
    return {"error": "Conversation not found"}
