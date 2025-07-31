# app/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Systemabhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY . .

# Port freigeben
EXPOSE 5000

# Anwendung starten
CMD ["python", "app.py"]
