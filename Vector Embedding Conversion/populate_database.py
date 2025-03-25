import argparse
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
import torch
import chromadb
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from display_image import search_images

# Load CLIP model and processor
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
CHROMA_PATH = "chroma"  # Ensure this matches your database path
DATA_PATH = "data"
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="image_embeddings")
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    
    query_rag(query_text)

def get_text_image_embedding(text):
    """Converts a text into an image embedding using CLIP."""
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    
    with torch.no_grad():
        text_image_features = model.get_text_features(**inputs)
    
    return text_image_features.squeeze().tolist()  # Convert tensor to list


def query_rag(query_text: str):
    # Prepare the DB.
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_score(query_text, k=5)

    if not results:
        print("No relevant documents found.")
        return "No relevant documents found."

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt_str = str(prompt_template.format(context=context_text, question=query_text))  # Convert to string

    model = Ollama(model="mistral")
    response_text = model.invoke(prompt_str)
     
    matched_images = search_images(query_text, similarity_threshold=0.89, top_k=2)
    sources = [doc.metadata.get("id", None) if hasattr(doc, 'metadata') else "Unknown" for doc, _ in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}\n Image Sources: {matched_images}"
    print(formatted_response)
    return response_text

if __name__ == "__main__":
    main()
