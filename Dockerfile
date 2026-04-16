# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY frontend/ .

# Build the application as static files
RUN npx nuxi generate

# Stage 2: Build Backend with Frontend Static Files
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend static files
COPY --from=frontend-builder /app/frontend/.output/public /app/public

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Start the backend server
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
