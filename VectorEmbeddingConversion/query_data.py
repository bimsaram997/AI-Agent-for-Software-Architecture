import argparse
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
from typing import List, Dict, Optional

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are an AI Software Architecture Assistant. Use the following context and conversation history to answer the question.

Context:
{context}

---

Conversation History:
{history}

---

Current Question: {question}

Provide a detailed, professional response focusing on software architecture best practices.
Include relevant examples when appropriate.
"""

def query_rag(query_text: str, conversation_history: Optional[List[Dict]] = None):
    if conversation_history is None:
        conversation_history = []
    
    # Prepare the DB
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    
    # Search the DB
    results = db.similarity_search_with_score(query_text, k=5)
    
    if not results:
        return "No relevant architectural documents found. Could you provide more details about your system?"
    
    # Format context and history
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    history_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" 
        for msg in conversation_history[-6:]  # Keep last 6 messages
    ) if conversation_history else "No previous conversation"
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt_str = str(prompt_template.format(
        context=context_text,
        history=history_text,
        question=query_text
    ))
    
    # Configure the remote Ollama instance
    model = Ollama(
        model="llama3.2:latest",
        base_url="http://86.50.169.115:11434",  
        temperature=0.7,
        top_p=0.9,
        timeout=60  
    )
    
    try:
        response_text = model.invoke(prompt_str)
    except Exception as e:
        return f"Error connecting to the AI model: {str(e)}"
    
    # Add image search
    sources = [doc.metadata.get("id", None) if hasattr(doc, 'metadata') else "Unknown" for doc, _ in results]
    formatted_sources = []
    print("Matched Sources Metadata:\n")
    
    for i, (doc, score) in enumerate(results, 1):
        metadata = doc.metadata
        author = metadata.get("author", "Unknown")
        creator = metadata.get("creator", "Unknown")
        source = metadata.get("source", metadata.get("id", "Unknown"))

        # For logging
        print(f"[Source {i}]")
        print(f"Score: {score}")
        print(f"Author: {author}")
        print(f"Creator: {creator}")
        print(f"Source: {source}")
        print(f"Content Preview: {doc.page_content[:200]}")
        print("-" * 50)
        
        formatted_sources.append(f"- Source {i}: Author: {author}, Creator: {creator}, Source: {source}")

    
    matched_images = search_images(query_text, similarity_threshold=0.89, top_k=2)
    if matched_images:
        response_text += f"\n\nRelated architecture diagrams: {matched_images}"
    
    if formatted_sources:
        sources_section = "\n\n**Sources:**\n" + "\n".join(formatted_sources)
        response_text += sources_section
    
    return response_text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    query_rag(query_text)

if __name__ == "__main__":
    main()