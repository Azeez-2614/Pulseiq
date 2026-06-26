FROM python:3.11-slim

# Install system dependencies needed for compiling python packages (e.g. databases, transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Default command runs the background scheduler pipeline
CMD ["python", "scheduler.py"]
