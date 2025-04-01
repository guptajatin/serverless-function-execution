# Use a minimal Python image
FROM python:3.9-slim

# Install system dependencies required for psutil
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set workdir inside the container
WORKDIR /app

# Copy files into the container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the dispatcher script
CMD ["uvicorn", "dispatcher:app", "--host", "0.0.0.0", "--port", "8000"]
