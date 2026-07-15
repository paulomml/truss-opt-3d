"""
Pacote de Engenharia — solvers físicos e verificações normativas.

Submódulos:
- `fea/`              — Solver PyNite (MEF 3D).
- `standards/`        — Verificações NBR 8800, 6120, 6123 (modular).
- `modelos_fisicos`   — Dataclasses de domínio (NoFisico, BarraFisica, etc).
"""
from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
    ResultadoAnalise,
    material_dict_para_fisico,
    perfil_dict_para_fisico,
)

__all__ = [
    "BarraFisica",
    "MaterialFisico",
    "NoFisico",
    "PerfilFisico",
    "ResultadoAnalise",
    "material_dict_para_fisico",
    "perfil_dict_para_fisico",
]
