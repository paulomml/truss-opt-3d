"""Pacote de núcleo da aplicação: configs, banco, Celery, cache, memória."""
from core.config import configuracoes, obter_configuracoes
from core.database import Base, SessionLocal, engine, obter_sessao, inicializar_banco
from core.cache import (
    gerar_chave_cache,
    obter_do_cache,
    salvar_no_cache,
    invalidar_cache,
    cliente_redis,
    definir_cliente_redis,
)
from core.memoria import (
    CanceladorOtimizacao,
    LimiteMemoriaExcedido,
    cancelador_global,
    verificar_memoria,
    uso_atual_percentual,
)

__all__ = [
    "configuracoes",
    "obter_configuracoes",
    "Base",
    "SessionLocal",
    "engine",
    "obter_sessao",
    "inicializar_banco",
    "gerar_chave_cache",
    "obter_do_cache",
    "salvar_no_cache",
    "invalidar_cache",
    "cliente_redis",
    "CanceladorOtimizacao",
    "LimiteMemoriaExcedido",
    "cancelador_global",
    "verificar_memoria",
    "uso_atual_percentual",
]
