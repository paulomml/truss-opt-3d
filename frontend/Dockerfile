# Frontend Dockerfile — truss-opt-3d
# Build multi-estágio: Node 24 + Nuxt 4 → servidor Node de produção.

# ============================================================
# Estágio 1: Build da aplicação Nuxt
# ============================================================
FROM node:24-slim AS construtor

WORKDIR /app

# Variáveis de ambiente para build.
ENV NUXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Copia manifestos de dependências (camada cacheável).
COPY package.json package-lock.json* ./

# Instala dependências.
RUN npm install --no-audit --no-fund --include=dev

# Copia o código-fonte.
COPY . .

# Argumento de build para URL da API (sobreposto em produção).
ARG API_URL_BASE=http://backend:8000
ENV API_URL_BASE=$API_URL_BASE

# Compila o Nuxt (gera .output/server/index.mjs).
RUN npm run build

# ============================================================
# Estágio 2: Servidor de produção enxuto
# ============================================================
FROM node:24-slim AS runtime

WORKDIR /app

# Variáveis de runtime.
ENV NODE_ENV=production \
    NUXT_HOST=0.0.0.0 \
    NUXT_PORT=3000

# Copia apenas o build final do estágio anterior.
COPY --from=construtor /app/.output ./.output

# Healthcheck simples.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

EXPOSE 3000

# Inicializa o servidor Node.
CMD ["node", ".output/server/index.mjs"]
