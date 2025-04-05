from langchain_community.embeddings.ollama import OllamaEmbeddings
from transformers import CLIPProcessor, CLIPModel
from langchain_community.embeddings.bedrock import BedrockEmbeddings
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def get_embedding_function():
    # Use Ollama embeddings instead of AWS Bedrock
    embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url="http://127.0.0.1:11434")

    return embeddings

def get_text_embedding(text):
    """Get normalized text embedding using CLIP."""
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    
    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
    return text_features.squeeze().numpy()