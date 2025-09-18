FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get -y install ffmpeg curl unzip git gcc build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 8080

# Clear any cached bytecode
RUN find . -name "*.pyc" -delete
RUN find . -name "__pycache__" -delete

# Start Supabase-powered backend with no auth
CMD ["python", "railway_supabase_noauth.py"]