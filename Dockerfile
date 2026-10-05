# OmniBioAI — HPC Policy Engine
# Purpose: Build the HPC policy engine API container.
# Author: Manish Kumar <manish@omnibioai.org>

# Base image
FROM python:3.11-slim

# System dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

EXPOSE 8003

# Entrypoint and default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
