# Backend Dockerfile: Python 3.12 + FastAPI + Celery + PyNite + DEAP
FROM python:3.12-slim

# Metadados.
LABEL org.opencontainers.image.title="truss-opt-3d backend"
LABEL org.opencontainers.image.description="API FastAPI para otimização de treliças 3D"
LABEL org.opencontainers.image.version="1.0.0"

# Diretório de trabalho.
WORKDIR /app

# Variáveis de ambiente Python: sem bufferização para logs em tempo real.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependências do sistema (build-essential para compilar numpy/scipy se necessário).
RUN     apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python primeiro (camada cacheável).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação.
COPY . .

# Cria diretório para logs.
RUN mkdir -p /var/log/truss

# Exposição da porta.
EXPOSE 8000

# Healthcheck via curl no endpoint /api/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Comando padrão: uvicorn com proxy-headers para nginx.
CMD ["uvicorn", "api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--workers", "1"]
