import argparse
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from display_image import search_images
CHROMA_PATH = "chroma"

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

    model = Ollama(model="llama3")
    response_text = model.invoke(prompt_str)

    matched_images = search_images(query_text, similarity_threshold=0.89, top_k=2)
    sources = [doc.metadata.get("id", None) if hasattr(doc, 'metadata') else "Unknown" for doc, _ in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}\n Image Sources: {matched_images}"
    print(formatted_response)
    return response_text

if __name__ == "__main__":
    main()
