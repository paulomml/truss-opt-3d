"""
Cache de baixo nível baseado em Redis para análises estruturais.

A análise MEF de uma mesma configuração geométrica é determinística: não
faz sentido recalcular quando o frontend envia payload idêntico. A chave
de cache é um hash SHA-256 do payload normalizado.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from typing import Any

import redis

from core.config import configuracoes

# Cliente Redis compartilhado (pool de conexões gerido pelo próprio redis-py).
# Inicialização lazy para permitir override em testes.
_cliente_redis: redis.Redis | None = None


def _obter_cliente() -> redis.Redis:
    """Retorna o cliente Redis singleton (lazy initialization)."""
    global _cliente_redis
    if _cliente_redis is None:
        _cliente_redis = redis.Redis.from_url(
            configuracoes.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _cliente_redis


def definir_cliente_redis(cliente: redis.Redis) -> None:
    """Permite injetar um cliente customizado (útil para testes com fakeredis)."""
    global _cliente_redis
    _cliente_redis = cliente


# Prefixo para chaves de análise estrutural.
_PREFIXO_ANALISE = "truss:analise:"
# TTL padrão: 6 horas (permite iteração rápida do usuário sem poluir o Redis).
_TTL_PADRAO = 6 * 3600


def gerar_chave_cache(payload: dict) -> str:
    """Gera uma chave determinística para o payload fornecido."""
    payload_serializado = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(payload_serializado.encode("utf-8")).hexdigest()
    return f"{_PREFIXO_ANALISE}{digest}"


def obter_do_cache(chave: str) -> Any | None:
    """Recupera um valor do cache. Retorna None se ausente ou em caso de erro."""
    try:
        valor = _obter_cliente().get(chave)
        if valor is None:
            return None
        return json.loads(valor)
    except (redis.RedisError, ConnectionError, OSError):
        # Cache indisponível: segue sem cache (degradação graciosa).
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def salvar_no_cache(chave: str, valor: Any, ttl: int = _TTL_PADRAO) -> None:
    """Persiste um valor no cache com TTL em segundos."""
    with contextlib.suppress(redis.RedisError, ConnectionError, OSError, TypeError):
        _obter_cliente().setex(chave, ttl, json.dumps(valor, default=str))


def invalidar_cache(chave: str) -> None:
    """Remove uma chave específica do cache."""
    with contextlib.suppress(redis.RedisError, ConnectionError, OSError):
        _obter_cliente().delete(chave)


def cliente_redis() -> redis.Redis:
    """Exposição controlada do cliente Redis para outros módulos."""
    return _obter_cliente()
