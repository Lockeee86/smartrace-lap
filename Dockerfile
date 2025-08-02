FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory structure
RUN mkdir -p static/css static/js templates

# Copy all files
COPY . .

# Set permissions
RUN chmod -R 755 static/

# Debug: List all files
RUN echo "=== Files in /app ===" && ls -la /app/
RUN echo "=== Files in /app/static ===" && ls -la /app/static/
RUN echo "=== Files in /app/static/css ===" && ls -la /app/static/css/ || echo "CSS dir not found"
RUN echo "=== Files in /app/static/js ===" && ls -la /app/static/js/ || echo "JS dir not found"

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD curl -f http://localhost:5000/ || exit 1

CMD ["python", "app.py"]
