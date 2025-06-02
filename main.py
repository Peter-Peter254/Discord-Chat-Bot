import subprocess
import threading
import uvicorn

def run_discord_bot():
    subprocess.run(["python", "scripts/discord_bot.py"])

if __name__ == "__main__":
    print("Running embed_store.py to initialize Chroma store...")
    result = subprocess.run(["python", "scripts/embed_store.py"])
    if result.returncode != 0:
        print("embed_store.py failed. Exiting.")
        exit(1)
    print("Chroma store ready. Starting services...")
    threading.Thread(target=run_discord_bot, daemon=True).start()
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
