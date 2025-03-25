import tkinter as tk
from tkinter import filedialog, messagebox
import chromadb
from get_embedding_function import get_text_embedding

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
CHROMA_PATH = "chroma"  # Ensure this matches your database path
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
    
    image_embedding = get_text_embedding(description)
    existing_data = collection.get(ids=[image_path])
    
    if existing_data["ids"]:
        messagebox.showinfo("Info", f"Skipping duplicate: {image_path}")
        return
    
    collection.add(
        embeddings=[image_embedding.tolist()],
        metadatas=[{"description": description, "image_path": image_path}],
        ids=[image_path]
    )
    messagebox.showinfo("Success", f"Added: {image_path}")

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
