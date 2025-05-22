from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_data import query_rag
from typing import Dict, List
import uuid
from ADR_query_rag import generate_architecture_report
app = FastAPI()

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

class OpenEndedQuery(BaseModel):
    query: str
    conversation_id: str = None

class ADRQuery(BaseModel):
    system_type: str
    functional_requirements: list
    non_functional_requirements:list
    architecture_preference: str
    conversation_id: str = None

# Route: structured initial query
@app.post("/structured-query")
def handle_structured_query(data: StructuredQuery):
    full_query = f"""System Type: {data.system_type}
Functional Requirements: {', '.join(data.functional_requirements)}
Non-Functional Requirements: {', '.join(data.non_functional_requirements)}
Preferred Architecture: {data.architecture_preference}

What is the best approach?"""

    conv_id = str(uuid.uuid4())
    conversation_db[conv_id] = [{"role": "user", "content": full_query}]

    result = query_rag(full_query, conversation_history=[])
    
    # Support both string and dict returns
    if isinstance(result, str):
        response_text = result
        images = []
        sources = []
    else:
        response_text = result.get("response", "")
        images = result.get("images", [])
        sources = result.get("sources", [])

    conversation_db[conv_id].append({"role": "assistant", "content": response_text})

    return {
        "response": response_text,
        "images": images,
        "sources": sources,
        "conversation_id": conv_id
    }

# Route: follow-up chat queries
@app.post("/query")
def handle_open_ended_query(data: OpenEndedQuery):
    conversation_history = []
    if data.conversation_id and data.conversation_id in conversation_db:
        conversation_history = conversation_db[data.conversation_id]

    conversation_history.append({"role": "user", "content": data.query})

    result = query_rag(data.query, conversation_history=conversation_history)

    if isinstance(result, str):
        response_text = result
        images = []
        sources = []
    else:
        response_text = result.get("response", "")
        images = result.get("images", [])
        sources = result.get("sources", [])

    conversation_history.append({"role": "assistant", "content": response_text})

    if data.conversation_id:
        conversation_db[data.conversation_id] = conversation_history

    return {
        "response": response_text,
        "images": images,
        "sources": sources
    }

# Route: ADR query
@app.post("/generate-adr")
def generate_adr(data: ADRQuery):
    conversation_history = []
    if data.conversation_id and data.conversation_id in conversation_db:
        conversation_history = conversation_db[data.conversation_id]

    user_input_summary = (
        f"System Type: {data.system_type}\n"
        f"Functional Requirements: {', '.join(data.functional_requirements)}\n"
        f"Non-Functional Requirements: {', '.join(data.non_functional_requirements)}\n"
        f"Architecture Preference: {data.architecture_preference}"
    )
    conversation_history.append({"role": "user", "content": user_input_summary})

    # Generate ADR markdown
    result = generate_architecture_report(
        system_type=data.system_type,
        functional_requirements=", ".join(data.functional_requirements),
        non_functional_requirements=", ".join(data.non_functional_requirements),
        architecture_preference=data.architecture_preference
    )

    adr_markdown = result.get("report", "No ADR content generated.")
    images = result.get("images", [])
    sources = result.get("sources", [])

    # Log assistant response
    conversation_history.append({"role": "assistant", "content": adr_markdown})

    # Save updated history
    conversation_db[data.conversation_id] = conversation_history

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
