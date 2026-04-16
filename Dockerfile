# AVISO: Este arquivo foi concebido especificamente para viabilizar o deploy no Render Free-Tier.
# Sendo assim, esta configuração unifica front-end e back-end em um único container, visto que o Render Free-Tier não suporta orquestração via docker-compose.yml.

# Estágio 1: Compilação do Front-end (Geração de Ativos Estáticos)
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Instalação de dependências do ecossistema Node.js.
COPY frontend/package*.json ./
RUN npm install

# Transferência do código-fonte e execução do build algorítmico via Nuxt/Nitro.
COPY frontend/ .
RUN npx nuxi generate

# Estágio 2: Ambiente de Execução Unificado (Back-end Python + Front-end Estático)
FROM python:3.11-slim

WORKDIR /app

# Instalação de dependências do sistema operacional para compilação de bibliotecas científicas.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Configuração do ambiente Python e instalação dos pacotes definidos no Pydantic e solver MEF.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Integração do código do back-end (API e Domínio).
COPY backend/ .

# Integração dos arquivos estáticos do front-end gerados no Estágio 1.
# Portanto, o back-end passa a servir a interface de usuário de forma integrada.
COPY --from=frontend-builder /app/frontend/.output/public /app/public

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Inicialização do servidor Uvicorn com suporte à porta dinâmica definida pela plataforma de deploy.
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
