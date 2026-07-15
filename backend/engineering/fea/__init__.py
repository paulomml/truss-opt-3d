"""Pacote de Análise por Elementos Finitos (FEA)."""

from engineering.fea.pynite_solver import (
    BANCO_SOLOS,
    calcular_lk_banzos,
    construir_e_resolver,
)

__all__ = [
    "construir_e_resolver",
    "calcular_lk_banzos",
    "BANCO_SOLOS",
]
