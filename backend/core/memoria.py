"""
Monitor de memória do processo — protege contra OOM em otimizações longas.

A análise MEF + Algoritmo Genético pode consumir muita RAM quando o catálogo
de perfis é grande ou a população é numerosa. Este módulo fornece um check
centralizado que deve ser chamado a cada geração do GA.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import psutil

from core.config import configuracoes


_logger = logging.getLogger(__name__)


class LimiteMemoriaExcedido(RuntimeError):
    """Lançada quando o consumo de RAM ultrapassa o limite configurado."""


def uso_atual_percentual() -> float:
    """Retorna o percentual de RAM utilizada pelo sistema."""
    return psutil.virtual_memory().percent


def verificar_memoria(contexto: str = "") -> None:
    """Lança exceção se a RAM estiver acima do limite configurado."""
    uso = uso_atual_percentual()
    if uso > configuracoes.limite_memoria_percentual:
        mensagem = (
            f"Uso de memória {uso:.1f}% excedeu o limite "
            f"{configuracoes.limite_memoria_percentual:.1f}% "
            f"(contexto: {contexto or 'geral'})."
        )
        _logger.error(mensagem)
        raise LimiteMemoriaExcedido(mensagem)


class CanceladorOtimizacao:
    """
    Sinalizador thread-safe para cancelar otimizações em andamento.

    O frontend pode cancelar uma tarefa Celery via API; o loop do GA verifica
    este sinal a cada geração e interrompe graciosamente.
    """

    def __init__(self) -> None:
        self._evento = threading.Event()
        self._motivo: Optional[str] = None

    def cancelar(self, motivo: str = "Cancelado pelo usuário.") -> None:
        """Marca o cancelamento e armazena o motivo."""
        self._motivo = motivo
        self._evento.set()

    @property
    def cancelado(self) -> bool:
        """Indica se o cancelamento foi solicitado."""
        return self._evento.is_set()

    @property
    def motivo(self) -> Optional[str]:
        """Motivo do cancelamento (se houver)."""
        return self._motivo

    def verificar(self, contexto: str = "") -> None:
        """Lança exceção se o cancelamento foi solicitado."""
        if self._evento.is_set():
            raise InterruptedError(
                f"Otimização cancelada: {self._motivo or 'motivo não informado'} "
                f"(contexto: {contexto or 'geral'})."
            )


# Instância singleton para cancelamento global entre threads.
cancelador_global = CanceladorOtimizacao()
