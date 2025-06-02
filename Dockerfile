# Use a minimal Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Always run embed_store + discord bot on container startup
ENTRYPOINT ["sh", "-c", "python embed_store.py && python discord_bot.py"]
