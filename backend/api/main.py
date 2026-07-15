"""
App FastAPI principal: ponto de entrada do backend.

Importa configurações, middlewares e roteadores. Executado via
uvicorn api.main:app no container Docker.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import router
from core.config import configuracoes
from core.database import inicializar_banco


# Configuração de logging estruturado.
logging.basicConfig(
    level=logging.INFO if not configuracoes.depurar else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Lifecycle: inicializa banco na primeira execução."""
    try:
        # Importa seed para garantir tabelas + dados.
        from seed.popular_banco import popular_banco
        popular_banco()
        _logger.info("Banco de dados inicializado com sucesso.")
    except Exception as e:
        _logger.warning(f"Banco indisponível na inicialização: {e}")
        _logger.warning("Endpoints que dependem de PostgreSQL podem falhar.")
    yield


app = FastAPI(
    title=configuracoes.nome_app,
    version=configuracoes.versao_app,
    description=(
        "API REST para otimização de treliças 3D via Algoritmo Genético, "
        "com verificação NBR 8800/6120/6123 e geração de memorial de cálculo."
    ),
    lifespan=ciclo_vida,
)

# CORS: permite o frontend Nuxt em dev/prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=configuracoes.cors_lista,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas da API.
app.include_router(router)


@app.get("/")
async def raiz() -> dict:
    """Endpoint raiz: redireciona para /docs."""
    return {
        "mensagem": "TRUSS-OPT 3D API",
        "documentacao": "/docs",
        "health": "/api/health",
    }
