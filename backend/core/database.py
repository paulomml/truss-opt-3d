"""
Gerenciamento da sessão SQLAlchemy e do engine global do PostgreSQL.

O engine é criado uma única vez por processo (pool de conexões reutilizável).
A fábrica de sessões SessionLocal deve ser utilizada via dependência FastAPI
em obter_sessao para garantir o fechamento adequado após cada requisição.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from core.config import configuracoes


# Engine global: o pool padrão do SQLAlchemy gerencia concorrência e reuso.
engine = create_engine(
    configuracoes.database_url,
    pool_pre_ping=True,  # Detecta conexões mortas antes de usá-las.
    echo=configuracoes.echo_sql,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

# Fábrica de sessões: cada chamada cria uma sessão transacional isolada.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM do projeto."""
    pass


def obter_sessao() -> Generator[Session, None, None]:
    """Dependência FastAPI que fornece uma sessão transacional por requisição."""
    sessao = SessionLocal()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


def inicializar_banco() -> None:
    """Cria todas as tabelas (usado em testes e na primeira inicialização)."""
    # Importação tardia para evitar importações circulares.
    from db import modelos  # noqa: F401

    Base.metadata.create_all(bind=engine)
