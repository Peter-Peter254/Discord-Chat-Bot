# Use a minimal Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run embedding once, then keep bot running
CMD ["sh", "-c", "python embed_store.py && python discord_bot.py"]
