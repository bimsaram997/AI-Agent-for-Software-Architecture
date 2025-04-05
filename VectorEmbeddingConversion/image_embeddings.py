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

def add_image_to_collection():
    image_path = filedialog.askopenfilename(title="Select an Image")
    if not image_path:
        return
    
    description = description_entry.get()
    if not description:
        messagebox.showerror("Error", "Please enter a description.")
        return
    
    # Copy the image to the target folder
    filename = os.path.basename(image_path)
    new_image_path = os.path.join(TARGET_FOLDER, filename)

    # Check if file already exists to avoid overwriting
    counter = 1
    while os.path.exists(new_image_path):
        name, ext = os.path.splitext(filename)
        new_image_path = os.path.join(TARGET_FOLDER, f"{name}_{counter}{ext}")
        counter += 1

    shutil.copy(image_path, new_image_path)

    # Generate embedding
    image_embedding = get_text_embedding(description)
    existing_data = collection.get(ids=[new_image_path])

    if existing_data["ids"]:
        messagebox.showinfo("Info", f"Skipping duplicate: {new_image_path}")
        return

    # Add to ChromaDB
    collection.add(
        embeddings=[image_embedding.tolist()],
        metadatas=[{"description": description, "image_path": new_image_path}],
        ids=[new_image_path]
    )
    messagebox.showinfo("Success", f"Added: {new_image_path}")

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

description_label = tk.Label(root, text="Enter Image Description:")
description_label.pack()

description_entry = tk.Entry(root, width=50)
description_entry.pack()

add_button = tk.Button(root, text="Add Image", command=add_image_to_collection)
add_button.pack(pady=10)

reset_button = tk.Button(root, text="Reset Collection", command=reset_image_embeddings_collection)
reset_button.pack(pady=10)

exit_button = tk.Button(root, text="Exit", command=root.quit)
exit_button.pack(pady=10)

root.mainloop()
