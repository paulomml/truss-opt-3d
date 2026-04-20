# Render Free-Tier workaround: Unificação de services em container único devido à falta de suporte a sidecars/orchestration.

FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npx nuxi generate

FROM python:3.11-slim

WORKDIR /app

# Build-essential necessário para compilação de dependências C-bound (numpy/scipy fallback).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Fallback: Ativos estáticos servidos via FastAPI/StaticFiles para simplificar a topologia de rede.
COPY --from=frontend-builder /app/frontend/.output/public /app/public

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
