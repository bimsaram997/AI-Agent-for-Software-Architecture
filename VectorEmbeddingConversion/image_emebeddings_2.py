import tkinter as tk
from tkinter import filedialog, messagebox
import chromadb
from get_embedding_function import get_text_embedding
import shutil
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define ChromaDB path and target storage folder
CHROMA_PATH = "chroma"
TARGET_FOLDER = r"D:\Software, Web & Cloud, Computing Sciences FM\Master Thesis\AI-Agent-for-Software-Architecture\Vector Embedding Conversion\data_images"

# Ensure the directory exists
os.makedirs(TARGET_FOLDER, exist_ok=True)

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(
    name="image_embeddings", metadata={"hnsw:space": "cosine"}
)

def add_images_to_collection():
    image_paths = filedialog.askopenfilenames(title="Select Images", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
    if not image_paths:
        return

    added_images = []
    
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        image_name, ext = os.path.splitext(filename)
        new_image_path = os.path.join(TARGET_FOLDER, filename)

        # Avoid overwriting existing files
        counter = 1
        while os.path.exists(new_image_path):
            new_image_path = os.path.join(TARGET_FOLDER, f"{image_name}_{counter}{ext}")
            counter += 1

        shutil.copy(image_path, new_image_path)

        # Use image filename as description
        description = image_name.replace("_", " ")  # Replace underscores with spaces for readability
        
        # Generate embedding
        image_embedding = get_text_embedding(description)
        existing_data = collection.get(ids=[new_image_path])

        if existing_data["ids"]:
            continue  # Skip duplicates

        # Add to ChromaDB
        collection.add(
            embeddings=[image_embedding.tolist()],
            metadatas=[{"description": description, "image_path": new_image_path}],
            ids=[new_image_path]
        )
        added_images.append(new_image_path)

    if added_images:
        messagebox.showinfo("Success", f"Added {len(added_images)} images successfully.")
    else:
        messagebox.showinfo("Info", "No new images were added.")

def reset_image_embeddings_collection():
    collection_name = "image_embeddings"
    chroma_client.delete_collection(name=collection_name)
    global collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )
    messagebox.showinfo("Success", f"Collection '{collection_name}' has been reset.")

# GUI setup
root = tk.Tk()
root.title("ChromaDB Image Embedding GUI")
root.geometry("400x250")

add_button = tk.Button(root, text="Add Images", command=add_images_to_collection)
add_button.pack(pady=10)

reset_button = tk.Button(root, text="Reset Collection", command=reset_image_embeddings_collection)
reset_button.pack(pady=10)

exit_button = tk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

root.mainloop()
