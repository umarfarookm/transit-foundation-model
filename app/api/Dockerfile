FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY inference/ ./inference/
COPY app/ ./app/
COPY scripts/config.py ./scripts/config.py
COPY scripts/__init__.py ./scripts/__init__.py

# HuggingFace Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
