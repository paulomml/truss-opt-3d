"""
Configuração do Celery para processamento assíncrono de otimizações.

O Celery utiliza Redis como broker e backend de resultados. As tarefas de
otimização são CPU-bound (MEF + GA), portanto cada worker consome uma tarefa
por vez (concorrência=1) para evitar estouro de memória.
"""
from __future__ import annotations

from celery import Celery
from kombu import Queue

from core.config import configuracoes


# Instância global do Celery — importada por `worker.tarefas`.
app_celery = Celery(
    "truss_opt_3d",
    broker=configuracoes.redis_url,
    backend=configuracoes.redis_url,
    include=["worker.tarefas"],
)

# Configurações operacionais.
app_celery.conf.update(
    # Tempo limite de execução por tarefa (segundos).
    task_time_limit=configuracoes.celery_tempo_limite_duro,
    task_soft_time_limit=configuracoes.celery_tempo_limite_suave,
    # Concorrência: 1 processo por worker (MEF é pesado).
    worker_concurrency=configuracoes.celery_max_concorrencia,
    # Prefetch: pega apenas 1 tarefa por vez.
    worker_prefetch_multiplier=1,
    # Resultados: expiram em 24h.
    result_expires=86400,
    # Fila única para tarefas de otimização.
    task_queues=(
        Queue("otimizacao", routing_key="otimizacao.#"),
        Queue("default", routing_key="default.#"),
    ),
    task_default_queue="default",
    task_routes={
        "worker.tarefas.otimizar_trelice_*": {"queue": "otimizacao"},
    },
    # Serialização JSON (compatível com Pinia no frontend via WebSocket).
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Tempo entre retries de conexão com o broker.
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,
)


@app_celery.task(bind=True)
def tarefa_diagnostico(self) -> dict:
    """Tarefa simples para validar a conectividade Celery + Redis."""
    return {
        "status": "ok",
        "mensagem": "Celery operante.",
        "task_id": self.request.id,
    }
