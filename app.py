import os
import threading
import time
import json
import shutil
from uuid import uuid4
import discord
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import chromadb
from tiktoken import get_encoding
from dotenv import load_dotenv


load_dotenv()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


store_path = "./chroma_store"
chroma_client = chromadb.PersistentClient(path=store_path)
collection = chroma_client.get_or_create_collection(name="railway_docs")


def initialize_embeddings():
    if os.path.exists(store_path):
        shutil.rmtree(store_path)
        print("Deleted existing ./chroma_store directory")

    with open("railway_docs_full.json", "r", encoding="utf-8") as f:
        documents = json.load(f)

    tokenizer = get_encoding("cl100k_base")

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


def run_discord_bot():
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    discord_client = discord.Client(intents=intents)

    @discord_client.event
    async def on_ready():
        print(f'Discord bot logged in as {discord_client.user.name}')

    @discord_client.event
    async def on_message(message):
        if message.author.bot:
            return

        query = None
        if message.content.startswith("!railway "):
            query = message.content[len("!railway "):]
        elif discord_client.user in message.mentions:
            query = message.content.replace(f"<@{discord_client.user.id}>", "").strip()

        if not query:
            return

        await message.channel.typing()

        try:
            response = requests.post(CHAT_API_URL, json={"question": query})
            data = response.json()
            answer = data.get("answer", "Sorry, I couldn't find an answer.")
            sources = "\n".join(f"[{s['title']}]({s['url']})" for s in data.get("sources", [])[:2])
            reply_content = f"**Answer:**\n{answer}\n\n**Sources:**\n{sources}"
            await message.reply(reply_content[:2000])  # Ensure message limit

        except Exception as e:
            print("API Error:", e)
            await message.reply(f"Error: {str(e)}")

    discord_client.run(TOKEN)


app = FastAPI()

class ChatRequest(BaseModel):
    question: str

@app.on_event("startup")
async def startup_event():
    initialize_embeddings()
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()

@app.get("/")
def root():
    return {"status": "RailwayDocsBot backend running"}

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
        {"role": "system", "content": "You are a helpful assistant answering questions about Railway's documentation."},
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