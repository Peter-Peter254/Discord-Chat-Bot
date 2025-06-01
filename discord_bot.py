import os
import discord
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHAT_API_URL = os.getenv("CHAT_API_URL")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user.name}#{client.user.discriminator}')

@client.event
async def on_message(message):
    print("📨 Message received:", message.content)

    if message.author.bot:
        return

    query = None

    if message.content.startswith("!railway "):
        query = message.content[len("!railway "):]
    elif client.user in message.mentions:
        query = message.content.replace(f"<@{client.user.id}>", "").strip()

    if not query:
        return

    await message.channel.typing()

    try:
        response = requests.post(CHAT_API_URL, json={"question": query})
        data = response.json()

        print("🧠 API Response:", data)

        answer = data.get("answer", "Sorry, I couldn't find an answer.")
        sources = "\n".join(f"[{s['title']}]({s['url']})" for s in data.get("sources", [])[:2])

        reply_content = f"**Answer:**\n{answer}\n\n**Sources:**\n{sources}"

        # Ensure message is <= 2000 characters
        if len(reply_content) > 2000:
            reply_content = reply_content[:1997] + "..."

        await message.reply(reply_content)

    except Exception as e:
        print("❌ API Error:", e)
        await message.reply(f"❌ Error querying the API: {e}")

client.run(TOKEN)
