FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get -y install ffmpeg curl unzip git gcc build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8080

# Force start AI-enabled no-auth FastAPI server with Deepgram
CMD ["uvicorn", "railway_noauth:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]