from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import chromadb

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection(name="railway_docs")

app = FastAPI()

class ChatRequest(BaseModel):
    question: str

@app.get("/")
def root():
    return {"status": "RailwayDocsBot backend running 🚂"}

@app.post("/chat")
def chat(req: ChatRequest):
    question = req.question

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )
    question_embedding = response.data[0].embedding


    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5
    )


    sources = []
    context = ""
    for doc, meta in list(zip(results["documents"][0], results["metadatas"][0]))[:2]:
        context += doc + "\n---\n"
        sources.append({
            "url": meta["url"],
            "title": meta.get("title", "Untitled")
        })

    
    messages = [
        {"role": "system", "content": "You are a helpful assistant answering questions about Railway's documentation. Cite URLs when relevant."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    chat_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    answer = chat_response.choices[0].message.content

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }
