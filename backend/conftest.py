"""
Configuração do pytest para o backend.

- Converte DB para SQLite em memória (testes unitários não dependem de PostgreSQL).
- Configura asyncio mode=auto.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório backend/ ao PYTHONPATH.
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# Override de configurações para usar SQLite em testes unitários.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORTA", "5432")
os.environ.setdefault("POSTGRES_USUARIO", "test")
os.environ.setdefault("POSTGRES_SENHA", "test")
os.environ.setdefault("POSTGRES_BANCO", "test_truss")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORTA", "6379")


import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from core import database as db_module
from core.cache import definir_cliente_redis
from core.database import Base, SessionLocal


@pytest.fixture(scope="session", autouse=True)
def configurar_banco_testes():
    """Substitui o engine PostgreSQL por SQLite em memória para testes rápidos.

    Usa StaticPool para compartilhar a mesma conexão (e o mesmo DB em memória)
    entre todas as threads/sessões do pytest.
    """
    engine_teste = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Substitui globalmente.
    db_module.engine = engine_teste
    db_module.SessionLocal.configure(bind=engine_teste)
    # Cria tabelas.
    from db import modelos  # noqa: F401

    Base.metadata.create_all(bind=engine_teste)
    # Popula com dados padrão.
    from seed.popular_banco import popular_banco

    popular_banco()

    # Substitui o cliente Redis por fakeredis (sem dependência externa).
    try:
        import fakeredis

        cliente_fake = fakeredis.FakeRedis(decode_responses=True)
        definir_cliente_redis(cliente_fake)
    except ImportError:
        pass  # fakeredis opcional: testes que não usam Redis ainda funcionam.

    yield
    engine_teste.dispose()


@pytest.fixture(autouse=True)
def mock_celery_delay(monkeypatch):
    """Mocka otimizar_trelice.delay para não disparar Celery real em testes."""
    from worker import tarefas

    def _delay_mock(*args, **kwargs):
        class _ResultadoFalso:
            id = "fake-celery-task-id"

        return _ResultadoFalso()

    monkeypatch.setattr(tarefas.otimizar_trelice, "delay", _delay_mock)


@pytest.fixture
def sessao_teste():
    """Sessão de banco isolada por teste."""
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.rollback()
        sessao.close()
