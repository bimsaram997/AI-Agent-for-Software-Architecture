import torch
import chromadb
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from sklearn.metrics.pairwise import cosine_similarity
from get_embedding_function import get_text_embedding
# Load CLIP model
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
CHROMA_PATH = "chroma"  # Ensure this matches your database path
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(
    name="image_embeddings", metadata={"hnsw:space": "cosine"}
)


def search_images(query, similarity_threshold=0.75, top_k=5):
    """Search for images similar to the query."""
    query_embedding = get_text_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["embeddings", "metadatas", "distances"]  # Ensure embeddings are requested
    )
    
    if not results.get("distances"):  # If "distances" is missing or empty
        print("⚠️ No results found.")
        return []
    
    matched_images = []
    
    for i, distance in enumerate(results["distances"][0]):
        image_path = results["metadatas"][0][i]["image_path"]

        # ✅ Fix: Handle missing embeddings safely
        if results.get("embeddings") is not None and len(results["embeddings"]) > 0:
            image_embedding = np.array(results["embeddings"][0][i])
            similarity = cosine_similarity([query_embedding], [image_embedding])[0][0]
            
            if similarity >= similarity_threshold:
                matched_images.append(image_path)
        else:
            print(f"⚠️ Warning: No embedding found for {image_path}, skipping.")

    return matched_images

def reset_image_embeddings_collection():
    """Reset the image embeddings collection."""
    collection_name = "image_embeddings"
    chroma_client.delete_collection(name=collection_name)
    print(f"Collection '{collection_name}' has been deleted.")
    
    global collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )
    print(f"Collection '{collection_name}' has been recreated.")

# Example usage
if __name__ == "__main__":
    # Reset collection (only run when needed)
    #reset_image_embeddings_collection()
    
    # Adding images to collection
    #add_image_to_collection("Client Server Architecture.jpg", "A detailed diagram of Client Server Architecture.")

    
    # Searching for relevant images
    query = "Tell me role of micro service architecture"
    matched_images = search_images(query, similarity_threshold=0.89, top_k=2)
    
    print("\nMatched Images:", matched_images)
