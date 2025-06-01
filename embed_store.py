import json
import os
import shutil
from uuid import uuid4
from openai import OpenAI
import chromadb
from tiktoken import get_encoding
from dotenv import load_dotenv

load_dotenv()

store_path = "./chroma_store"
if os.path.exists(store_path):
    shutil.rmtree(store_path)
    print("Deleted existing ./chroma_store directory")

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


with open("railway_docs_full.json", "r", encoding="utf-8") as f:
    documents = json.load(f)

# Tokenizer for chunking
tokenizer = get_encoding("cl100k_base")

# Init Chroma persistent vector store
chroma_client = chromadb.PersistentClient(path=store_path)
collection = chroma_client.get_or_create_collection(name="railway_docs")

# Chunking function
def chunk_text(text, max_tokens=500, overlap=50):
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk = tokenizer.decode(tokens[start:end])
        chunks.append(chunk)
        start += max_tokens - overlap
    return chunks

# Embed each chunk
for doc in documents:
    url = doc["url"]
    chunks = chunk_text(doc["content"])

    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid4())
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            )
            embedding = response.data[0].embedding
            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "url": url,
                    "chunk": i,
                    "title": doc.get("title", "Untitled")
                }]
            )
        except Exception as e:
            print(f"Failed to embed chunk {i} from {url}: {e}")

print("Vector store created and saved to ./chroma_store")
