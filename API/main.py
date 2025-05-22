from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_data import query_rag  # Your RAG logic

app = FastAPI()

# Allow requests from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" allows all origins; you can specify Streamlit's URL to restrict it
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input schema for structured query
class StructuredQuery(BaseModel):
    system_type: str
    functional_requirements: list
    non_functional_requirements:list
    architecture_preference: str

# Input schema for open-ended query
class OpenEndedQuery(BaseModel):
    query: str

# Endpoint for RAG-based response (structured)
@app.post("/structured-query")
def handle_structured_query(data: StructuredQuery):
    # Create the query from structured inputs
    full_query = f"System Type: {data.system_type}\nFunctional Requirements: {', '.join(data.functional_requirements)}\nNon-Functional Requirements: {', '.join(data.non_functional_requirements)}\nPreferred Architecture: {data.architecture_preference}\n\nWhat is the best approach?"
    response_text = query_rag(full_query)
    return {"response": response_text}

# Endpoint for open-ended query (chat)
@app.post("/query")
def handle_open_ended_query(data: OpenEndedQuery):
    response_text = query_rag(data.query)
    return {"response": response_text}
