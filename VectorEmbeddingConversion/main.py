from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_data import query_rag
from typing import Dict, List
import uuid

app = FastAPI()

# Conversation memory storage
conversation_db: Dict[str, List[Dict]] = {}

# Allow requests from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input schema for structured query
class StructuredQuery(BaseModel):
    system_type: str
    key_requirements: list
    architecture_preference: str

# Input schema for open-ended query
class OpenEndedQuery(BaseModel):
    query: str
    conversation_id: str = None

@app.post("/structured-query")
def handle_structured_query(data: StructuredQuery):
    # Create the query from structured inputs
    full_query = f"""System Type: {data.system_type}
Key Requirements: {', '.join(data.key_requirements)}
Preferred Architecture: {data.architecture_preference}

What is the best approach?"""
    
    # Create new conversation
    conv_id = str(uuid.uuid4())
    conversation_db[conv_id] = [
        {"role": "user", "content": full_query}
    ]
    
    response_text = query_rag(full_query, conversation_history=[])
    conversation_db[conv_id].append({"role": "assistant", "content": response_text})
    
    return {
        "response": response_text,
        "conversation_id": conv_id
    }

@app.post("/query")
def handle_open_ended_query(data: OpenEndedQuery):
    conversation_history = []
    if data.conversation_id and data.conversation_id in conversation_db:
        conversation_history = conversation_db[data.conversation_id]
    
    # Add new user message to history
    conversation_history.append({"role": "user", "content": data.query})
    
    # Get response with full context
    response_text = query_rag(data.query, conversation_history)
    
    # Update conversation history
    conversation_history.append({"role": "assistant", "content": response_text})
    
    if data.conversation_id:
        conversation_db[data.conversation_id] = conversation_history
    
    return {"response": response_text}

@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    if conversation_id in conversation_db:
        return {"conversation": conversation_db[conversation_id]}
    return {"error": "Conversation not found"}