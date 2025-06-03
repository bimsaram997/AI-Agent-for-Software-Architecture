import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embedding_function import get_embedding_function
from langchain_community.vectorstores import Chroma

# Constants
CHROMA_PATH = "chroma"
DATA_PATH = "data"

# Ensure the data directory exists
os.makedirs(DATA_PATH, exist_ok=True)

# Tkinter App
class DocumentProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Document Upload and Processing")
        self.root.geometry("400x350")

        # File Upload Section
        self.file_label = tk.Label(root, text="Upload PDF Documents", font=("Arial", 12))
        self.file_label.pack(pady=10)

        self.upload_button = tk.Button(root, text="Upload Files", command=self.upload_files)
        self.upload_button.pack(pady=5)

        # Document Type Selection
        self.type_label = tk.Label(root, text="Select Document Type", font=("Arial", 12))
        self.type_label.pack(pady=10)

        self.document_type = tk.StringVar(value="Architecture Decision Record")
        self.type_menu = tk.OptionMenu(root, self.document_type, "Architecture Decision Record", "Anti Patterns", "Benchmarking", "Best Practises",  "Case studies",  "Software Enginnering Literatures",  
                                       "Software Architecture Patterns", "Architecture examples best")
        self.type_menu.pack(pady=5)

        # Process Button
        self.process_button = tk.Button(root, text="Process Documents", command=self.process_documents)
        self.process_button.pack(pady=20)

        # Clear Database Button
        self.clear_button = tk.Button(root, text="Clear Database", command=self.clear_database)
        self.clear_button.pack(pady=10)

        # Status Label
        self.status_label = tk.Label(root, text="", font=("Arial", 10))
        self.status_label.pack(pady=10)

    def upload_files(self):
        files = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf")])
        if files:
            duplicate_files = self.check_for_duplicates(files)
            if duplicate_files:
                response = messagebox.askyesno("Duplicate Files", f"The following files already exist:\n{', '.join(duplicate_files)}\nDo you want to overwrite them?")
                if not response:
                    return  # Skip uploading if the user chooses not to overwrite

            for file_path in files:
                file_name = os.path.basename(file_path)
                shutil.copy(file_path, os.path.join(DATA_PATH, file_name))
            self.status_label.config(text=f"{len(files)} files uploaded successfully.")
            messagebox.showinfo("Success", f"{len(files)} files uploaded successfully.")

    def check_for_duplicates(self, files):
        duplicate_files = []
        for file_path in files:
            file_name = os.path.basename(file_path)
            if os.path.exists(os.path.join(DATA_PATH, file_name)):
                duplicate_files.append(file_name)
        return duplicate_files

    def process_documents(self):
        document_type = self.document_type.get()
        self.status_label.config(text="Processing documents...")
        self.root.update()  # Update the UI to show the status

        documents = self.load_documents(document_type)
        cleaned_documents = self.clean_and_preprocess_documents(documents)
        chunks = self.split_documents(cleaned_documents)
        self.add_to_chroma(chunks)

        self.status_label.config(text="Documents processed and added to the database.")
        messagebox.showinfo("Success", "Documents processed and added to the database.")

    def clean_and_preprocess_documents(self, documents):
        cleaned_documents = []
        for document in documents:
            # Clean the text
            cleaned_text = self.clean_text(document.page_content)
            # Update the document with cleaned text
            document.page_content = cleaned_text
            cleaned_documents.append(document)
        return cleaned_documents

    def clean_text(self, text):
        # Remove special characters and extra spaces
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)  # Keep only alphanumeric and spaces
        text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with a single space
        text = text.strip()  # Remove leading/trailing spaces
        text = text.lower()  # Convert to lowercase
        return text

    def clear_database(self):
        if os.path.exists(CHROMA_PATH):
            shutil.rmtree(CHROMA_PATH)
            self.status_label.config(text="Database cleared.")
            messagebox.showinfo("Success", "Database cleared.")

    def load_documents(self, document_type):
        document_loader = PyPDFDirectoryLoader(DATA_PATH)
        documents = document_loader.load()
        
        # Add the document type to each document's metadata
        for document in documents:
            document.metadata["type"] = document_type
        
        return documents

    def split_documents(self, documents: list[Document]):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=80,
            length_function=len,
            is_separator_regex=False,
        )
        return text_splitter.split_documents(documents)

    def add_to_chroma(self, chunks: list[Document]):
        db = Chroma(
            persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
        )

        # Calculate Page IDs.
        chunks_with_ids = self.calculate_chunk_ids(chunks)

        # Add or Update the documents.
        existing_items = db.get(include=[])  # IDs are always included by default
        existing_ids = set(existing_items["ids"])
        print(f"Number of existing documents in DB: {len(existing_ids)}")

        # Only add documents that don't exist in the DB.
        new_chunks = [chunk for chunk in chunks_with_ids if chunk.metadata["id"] not in existing_ids]
        if new_chunks:
            print(f"👉 Adding new documents: {len(new_chunks)}")
            new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
            db.add_documents(new_chunks, ids=new_chunk_ids)
            db.persist()
        else:
            print("✅ No new documents to add")

    def calculate_chunk_ids(self, chunks):
        last_page_id = None
        current_chunk_index = 0

        for chunk in chunks:
            source = chunk.metadata.get("source")
            page = chunk.metadata.get("page")
            current_page_id = f"{source}:{page}"

            # If the page ID is the same as the last one, increment the index.
            if current_page_id == last_page_id:
                current_chunk_index += 1
            else:
                current_chunk_index = 0

            # Calculate the chunk ID.
            chunk_id = f"{current_page_id}:{current_chunk_index}"
            last_page_id = current_page_id

            # Add it to the page meta-data.
            chunk.metadata["id"] = chunk_id

        return chunks

# Run the Tkinter App
if __name__ == "__main__":
    root = tk.Tk()
    app = DocumentProcessorApp(root)
    root.mainloop()