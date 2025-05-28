from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query_data import query_rag  # Your RAG logic
from fastapi.staticfiles import StaticFiles
import os
app = FastAPI()

# Allow requests from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" allows all origins; you can specify Streamlit's URL to restrict it
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

pdf_dir = os.path.abspath("chroma/VectorEmbeddingConversion/data")
print("✅ Serving PDF directory from:", pdf_dir)

if not os.path.exists(pdf_dir):
    raise RuntimeError(f"Directory not found: {pdf_dir}")

print("📄 Available files:")
for f in os.listdir(pdf_dir):
    print("  -", f)

app.mount("/files", StaticFiles(directory=pdf_dir), name="files")


# Optional: quick test
@app.get("/ping")
def ping():
    return {"message": "pong"}
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
