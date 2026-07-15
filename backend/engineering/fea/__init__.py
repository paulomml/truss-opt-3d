"""Pacote de Análise por Elementos Finitos (FEA)."""
from engineering.fea.pynite_solver import (
    construir_e_resolver,
    calcular_lk_banzos,
    BANCO_SOLOS,
)

__all__ = [
    "construir_e_resolver",
    "calcular_lk_banzos",
    "BANCO_SOLOS",
]
