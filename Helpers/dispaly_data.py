from langchain_community.vectorstores import Chroma
from get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"  # Ensure this matches your database path

def check_database():
    # Load the database
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embedding_function())

    # Fetch stored document details (text, metadata, embeddings)
    data = db.get(include=["documents", "metadatas", "embeddings"])  # Include documents, metadata, and embeddings
    print(f"📂 Number of documents in DB: {len(data['ids'])}")

    # Iterate through the full dataset
    for i in range(len(data['ids'])):  # Fetch all documents
        print("\n--- Document Sample ---")
        print(f"🆔 ID: {data['ids'][i]}")  # Document ID
        print(f"📄 Text: {data['documents'][i][:500]}...")  # First 500 characters of the document text
        print(f"📑 Metadata: {data['metadatas'][i]}")  # Metadata
        print(f"🧠 Embedding: {data['embeddings'][i][:10]}...")  # Show first 10 values of the embedding (to keep it readable)

if __name__ == "__main__":
    check_database()
